"""Read-only impact of strict project scope on the verified active consolidated artifact."""

import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime

BASE = 'gs://gglobo-viu-dados-hdg-prd-ppd-pipeline-monday/consolidado/diario/'
RULE = 'entrada-primeiro-status-conhecido-v1'


def instant(value):
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.utcoffset() is None:
        raise ValueError('Data sem fuso')
    return parsed


def assess(group):
    """Creation-day equality deliberately not required. Never synthesizes events."""
    ordered = sorted(group, key=lambda r: r['ordem_etapa'])
    known = [r for r in ordered if (r.get('status_nome') or '').strip()]
    if not known:
        return ['sem_status_conhecido'], 0
    first = known[0]
    reasons = set()
    if first['status_nome'].strip().casefold() != 'entrada':
        reasons.add('primeiro_status_conhecido_nao_e_entrada')
    start = instant(first.get('entrada_status_utc'))
    if start is None:
        reasons.add('entrada_sem_data')
    prefix = ordered[:ordered.index(first)]
    for row in prefix:
        at, end = instant(row.get('entrada_status_utc')), instant(row.get('saida_status_utc'))
        if start is None or at is None or at >= start or (end is not None and end > start):
            reasons.add('prefixo_nulo_sem_ordem_comprovada')
    timeline = ordered[len(prefix):]
    for i, row in enumerate(timeline):
        at, end = instant(row.get('entrada_status_utc')), instant(row.get('saida_status_utc'))
        if not (row.get('status_nome') or '').strip() or row.get('status_terminal') is None:
            reasons.add('status_desconhecido_apos_entrada')
        if at is None or (end is not None and end < at):
            reasons.add('limites_invalidos')
        if i:
            previous = timeline[i - 1]
            if at is None or instant(previous.get('saida_status_utc')) != at:
                reasons.add('lacuna_ou_sobreposicao')
            if previous['ambiente_origem'] != row['ambiente_origem']:
                reasons.add('continuidade_entre_ambientes_nao_homologada')
    return sorted(reasons), len(prefix)


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row['projeto_id']].append(row)
    counts = Counter()
    retained = passages = prefixes = 0
    for group in groups.values():
        reasons, prefix = assess(group)
        if reasons:
            counts.update(reasons)
        else:
            retained += 1
            passages += len(group) - prefix
            prefixes += prefix
    return {'rule': RULE, 'projetos_atuais': len(groups), 'projetos_candidatos': retained,
            'projetos_excluidos': len(groups) - retained, 'passagens_candidatas': passages,
            'registros_nulos_pre_entrada_separados': prefixes,
            'motivos_por_projeto_nao_somar': dict(counts), 'cloud_modified': False,
            'limite': 'Sem lacunas detectadas nao comprova completude vitalicia; projetos abertos permitidos.'}


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
        raise ValueError('Publicacao mudou ou contagem divergente')
    print(json.dumps(summarize(rows), indent=2, ensure_ascii=True))


if __name__ == '__main__':
    main()
