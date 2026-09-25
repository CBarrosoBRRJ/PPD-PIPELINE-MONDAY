"""Daily project-level consumption split; no new identities or fabricated transitions."""

import json
from collections import Counter, defaultdict

from sls_orcamento_ppd.rules.business_time import BusinessCalendar

from monday_sla_orcamento.consolidation import validate
from monday_sla_orcamento.trajectory import instant

SLA = 'monday_sla_orcamento'
QUEUE = 'monday_fila_precificacao'
QUALITY = 'monday_sla_baixa_qualidade_de_dado'
RULE = 'destinos-projeto-v1'
COMMON = {
    'projeto_id': ('STRING', True), 'projeto_nome': ('STRING', False),
    'item_id_viu2': ('INTEGER', True), 'item_id_globocorp': ('INTEGER', True),
    'quantidade_passagens': ('INTEGER', True), 'status_atual': ('STRING', False),
    'cadastro_capturado_em': ('TIMESTAMP', True), 'corte_historico_utc': ('TIMESTAMP', True),
    'marca': ('STRING', False), 'talento': ('STRING', False),
    'eh_interveniencia': ('BOOLEAN', False), 'cadastro_atual_json': ('STRING', True),
    'versao_regra': ('STRING', True),
}
QUEUE_FIELDS = {**COMMON, 'entrada_fila_utc': ('TIMESTAMP', True),
                'espera_ate_utc': ('TIMESTAMP', True), 'espera_horas_corridas': ('FLOAT', True),
                'espera_horas_uteis': ('FLOAT', True), 'versao_calendario': ('STRING', True)}
QUALITY_FIELDS = {**COMMON, 'motivos_json': ('STRING', True),
                  'primeiro_status_conhecido': ('STRING', False),
                  'primeira_entrada_observada_utc': ('TIMESTAMP', False),
                  'evidencias_passagens_json': ('STRING', True)}


def reasons_for(group):
    known = [r for r in group if (r.get('status_nome') or '').strip()]
    if not known:
        return ['sem_status_conhecido'], 0
    first = known[0]
    prefix = group.index(first)
    start = instant(first['entrada_status_utc'])
    reasons = set()
    if first['status_nome'].strip().casefold() != 'entrada':
        reasons.add('primeiro_status_conhecido_nao_e_entrada')
    if start is None:
        reasons.add('entrada_sem_data')
    for row in group[:prefix]:
        at, end = instant(row['entrada_status_utc']), instant(row['saida_status_utc'])
        if start is None or at is None or at >= start or (end is not None and end > start):
            reasons.add('prefixo_nulo_sem_ordem_comprovada')
    for i, row in enumerate(group[prefix:]):
        if not (row.get('status_nome') or '').strip() or row['status_terminal'] is None:
            reasons.add('status_desconhecido_apos_entrada')
        if i:
            previous = group[prefix + i - 1]
            if instant(previous['saida_status_utc']) != instant(row['entrada_status_utc']):
                reasons.add('lacuna_ou_sobreposicao')
            if previous['ambiente_origem'] != row['ambiente_origem']:
                reasons.add('continuidade_entre_ambientes_nao_homologada')
    return sorted(reasons), prefix


def build(rows):
    """Validates the full input; splits whole projects; recalculated without a denylist."""
    validate(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[row['projeto_id']].append(row)
    output = {SLA: [], QUEUE: [], QUALITY: []}
    reasons_count = Counter()
    calendar = BusinessCalendar('America/Sao_Paulo')
    for project_id, group in sorted(groups.items()):
        group.sort(key=lambda r: r['ordem_etapa'])
        raw_contexts = {r['cadastro_atual_origem_json'] for r in group}
        if len(raw_contexts) != 1 or None in raw_contexts:
            raise ValueError('Destinos: cadastro ausente/divergente')
        context_raw = next(iter(raw_contexts))
        context = json.loads(context_raw)
        if 'status_nome' not in context or not context.get('capturado_em'):
            raise ValueError('Destinos: status/captura ausente')
        captured = instant(context['capturado_em'])
        first = group[0]
        common = {
            'projeto_id': project_id, 'projeto_nome': first['projeto_nome'],
            'item_id_viu2': first['item_id_viu2'], 'item_id_globocorp': first['item_id_globocorp'],
            'quantidade_passagens': len(group), 'status_atual': context['status_nome'],
            'cadastro_capturado_em': captured.isoformat(),
            'corte_historico_utc': first['corte_globocorp_utc'],
            'marca': first['cadastro_atual_marca'], 'talento': first['talento_nome_atual'],
            'eh_interveniencia': first['eh_interveniencia'], 'cadastro_atual_json': context_raw,
            'versao_regra': RULE,
        }
        reasons, prefix = reasons_for(group)
        timeline = group[prefix:]
        if not reasons and len(timeline) == 1:
            entry = timeline[0]
            start = instant(entry['entrada_status_utc'])
            if entry['saida_status_utc'] is not None:
                reasons.append('entrada_encerrada_sem_etapa_seguinte')
            elif (context['status_nome'] or '').strip().casefold() != 'entrada':
                reasons.append('entrada_isolada_diverge_cadastro_atual')
            elif start > captured:
                raise ValueError('Destinos: captura anterior a Entrada')
            else:
                output[QUEUE].append({**common, 'entrada_fila_utc': start.isoformat(),
                    'espera_ate_utc': captured.isoformat(),
                    'espera_horas_corridas': round((captured - start).total_seconds() / 3600, 3),
                    'espera_horas_uteis': round(calendar.hours(start, captured), 3),
                    'versao_calendario': calendar.version})
                continue
        if reasons:
            reasons_count.update(reasons)
            known = [r for r in group if (r['status_nome'] or '').strip()]
            entries = [r['entrada_status_utc'] for r in group
                       if (r['status_nome'] or '').strip().casefold() == 'entrada']
            evidence = [{k: r[k] for k in ('interval_id', 'ambiente_origem', 'item_id',
                        'ordem_etapa', 'status_nome', 'entrada_status_utc', 'saida_status_utc')}
                        for r in group]
            output[QUALITY].append({**common, 'motivos_json': json.dumps(sorted(reasons)),
                'primeiro_status_conhecido': known[0]['status_nome'] if known else None,
                'primeira_entrada_observada_utc': entries[0] if entries else None,
                'evidencias_passagens_json': json.dumps(evidence, ensure_ascii=False)})
        else:
            # Keep pre-Entrada NULL records as evidence, with their existing non-KPI values.
            # No reordering/renumbering or loss of original interval IDs.
            output[SLA].extend(group)
    ids = [{r['projeto_id'] for r in output[name]} for name in (SLA, QUEUE, QUALITY)]
    if any(ids[i] & ids[j] for i in range(3) for j in range(i + 1, 3)):
        raise ValueError('Destinos: projeto em dois destinos')
    represented = len(output[SLA]) + sum(r['quantidade_passagens']
                                       for name in (QUEUE, QUALITY) for r in output[name])
    if set.union(*ids) != set(groups) or represented != len(rows):
        raise ValueError('Destinos: reconciliacao divergente')
    validate(output[SLA])
    return output, {'rule': RULE, 'source_projects': len(groups), 'source_passages': len(rows),
                    'destinations': {name: {'rows': len(data),
                         'projects': len({r['projeto_id'] for r in data})}
                         for name, data in output.items()},
                    'quality_reasons': dict(reasons_count), 'balanced': True,
                    'scope': 'projetos selecionados pela consolidacao; nao inclui sem mapa'}
