"""Read-only, disjoint project destinations; consumes the existing strict-start audit."""

import hashlib
import json
import subprocess
from collections import Counter, defaultdict

from audit_project_start_cloudshell import BASE, assess, instant

SLA = 'monday_sla_orcamento'
QUEUE = 'monday_fila_precificacao'
QUALITY = 'monday_sla_baixa_qualidade_de_dado'
RULE = 'destinos-projeto-v1'


def partition(rows):
    """No mutation or new identities. All original passages stay with their project."""
    groups = defaultdict(list)
    seen = set()
    for row in rows:
        if row['interval_id'] in seen:
            raise ValueError('Passagem duplicada')
        seen.add(row['interval_id'])
        groups[row['projeto_id']].append(row)
    output = {SLA: [], QUEUE: [], QUALITY: []}
    decisions = []
    for project_id, group in sorted(groups.items()):
        group = sorted(group, key=lambda r: r['ordem_etapa'])
        if [r['ordem_etapa'] for r in group] != list(range(1, len(group) + 1)):
            raise ValueError('Ordem de projeto invalida')
        contexts = {r.get('cadastro_atual_origem_json') for r in group}
        if len(contexts) != 1 or None in contexts:
            raise ValueError('Cadastro atual ausente ou divergente')
        context = json.loads(next(iter(contexts)))
        if (context.get('board_id') != 18429499488
                or any(context.get('item_id') != r['item_id_globocorp'] for r in group)
                or 'status_nome' not in context or not context.get('capturado_em')):
            raise ValueError('Cadastro sem identidade/status/captura verificavel')
        captured = instant(context['capturado_em'])
        if captured is None:
            raise ValueError('Captura ausente')
        reasons, prefix = assess(group)
        known = group[prefix:]
        destination = QUALITY if reasons else SLA
        if not reasons and len(known) == 1:
            entry = known[0]
            if entry['saida_status_utc'] is not None:
                reasons.append('entrada_encerrada_sem_etapa_seguinte')
            elif (context['status_nome'] or '').strip().casefold() != 'entrada':
                reasons.append('entrada_isolada_diverge_cadastro_atual')
            elif instant(entry['entrada_status_utc']) > captured:
                raise ValueError('Captura anterior a Entrada')
            else:
                destination = QUEUE
            if reasons:
                destination = QUALITY
        output[destination].extend(group)
        decisions.append({'projeto_id': project_id, 'destino': destination,
                          'motivos': sorted(reasons), 'registros_nulos_pre_entrada': prefix})
    # Project-level partition preserves every input passage for auditability.
    if sum(len(v) for v in output.values()) != len(rows):
        raise ValueError('Particao nao reconciliada')
    return output, decisions


def summarize(rows):
    output, decisions = partition(rows)
    reasons = Counter(reason for d in decisions for reason in d['motivos'])
    return {'rule': RULE, 'cloud_modified': False,
            'scope': 'populacao atualmente consolidada; nao inclui itens sem mapa',
            'destinos': {name: {'projetos': len({r['projeto_id'] for r in values}),
                                'passagens': len(values)} for name, values in output.items()},
            'motivos_baixa_qualidade_nao_somar': dict(reasons),
            'projetos_reconciliados': len(decisions), 'passagens_reconciliadas': len(rows)}


def main():
    def read(path):
        return subprocess.check_output(['gcloud', 'storage', 'cat', BASE + path])
    before = read('control.json')
    control = json.loads(before)
    if control['pending'] is not None:
        raise ValueError('Publicacao pendente')
    active = control['active']
    if not active['artifact'].startswith('generations/') or '..' in active['artifact']:
        raise ValueError('Artefato inesperado')
    raw = read(active['artifact'])
    if hashlib.sha256(raw).hexdigest() != active['sha256']:
        raise ValueError('Checksum divergente')
    rows = [json.loads(line) for line in raw.splitlines()]
    if len(rows) != active['rows'] or read('control.json') != before:
        raise ValueError('Controle/contagem mudou')
    print(json.dumps(summarize(rows), indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
