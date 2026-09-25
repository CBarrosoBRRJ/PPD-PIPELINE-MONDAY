"""Four related analytical destinations, rebuilt from the selected source population."""
import json
from collections import defaultdict

from sls_orcamento_ppd.rules.business_time import BusinessCalendar

from monday_sla_orcamento.consolidation import FIELDS as BASE_FIELDS
from monday_sla_orcamento.cycle_contract import FIELDS as CYCLE_FIELDS
from monday_sla_orcamento.cycle_contract import TABLE as CYCLES
from monday_sla_orcamento.cycle_contract import project as cycle_rows
from monday_sla_orcamento.destinations import (
    QUALITY,
    QUALITY_FIELDS,
    QUEUE,
    QUEUE_FIELDS,
    RULE,
    SLA,
)
from monday_sla_orcamento.destinations import build as old_split
from monday_sla_orcamento.live_cycles import build as live_build
from monday_sla_orcamento.publication import canonical

VERSION = 'destinos-ciclos-v2'
# Nullable storage enables a recoverable additive migration; values validated below.
EXTRA = {
    'ciclo_id': ('STRING', False),
    'sla_categoria_tempo': ('STRING', False),
    'sla_grupo_permanencia_id': ('STRING', False),
    'sla_continuacao_mesmo_status': ('BOOLEAN', False),
    'sla_retorno_status': ('BOOLEAN', False),
    'sla_origem_duracao': ('STRING', False),
    'sla_referencia_ate_utc': ('TIMESTAMP', False),
    'sla_saida_estimada_utc': ('TIMESTAMP', False),
    'sla_horas_corridas': ('FLOAT', False),
    'sla_horas_uteis': ('FLOAT', False),
    'sla_motivos_json': ('STRING', False),
    'sla_versao_regra': ('STRING', False),
}
CONTRACTS = {SLA: {**BASE_FIELDS, **EXTRA}, QUEUE: QUEUE_FIELDS,
             QUALITY: QUALITY_FIELDS, CYCLES: CYCLE_FIELDS}


def projection(p):
    return dict(zip(EXTRA, [p['ciclo_id'], p['categoria'], p['grupo_permanencia_id'],
        p['eh_continuacao_mesmo_status'], p['eh_retorno_status'], p['origem_duracao'],
        p['referencia_ate_utc'], p['saida_estimada_utc'], p['horas_corridas'], p['horas_uteis'],
        json.dumps(p['motivos'], ensure_ascii=False), 'ciclos-continuos-v1'], strict=True))


def build(rows):
    base = canonical(rows)
    if not base:
        raise ValueError('Ciclos: populacao vazia')
    cuts = {r['corte_globocorp_utc'] for r in base}
    if len(cuts) != 1:
        raise ValueError('Ciclos: cortes divergentes')
    result = live_build(base, BusinessCalendar('America/Sao_Paulo'), cut=next(iter(cuts)))
    passages = {p['interval_id']: p for p in result['passagens']}
    excluded = {r['projeto_id']: r['motivo'] for r in result['excluidos']}
    old, _ = old_split(base)
    # Queue is a convenience subset, no longer an exclusive partition.
    outputs = {SLA: [{**r, **projection(passages[r['interval_id']])} for r in base
                     if r['interval_id'] in passages],
               QUEUE: [r for r in old[QUEUE] if r['projeto_id'] not in excluded],
               QUALITY: [], CYCLES: cycle_rows(result)}
    groups = defaultdict(list)
    for row in base:
        groups[row['projeto_id']].append(row)
    for project, group in sorted(groups.items()):
        group.sort(key=lambda r: r['ordem_etapa'])
        reasons = ({excluded[project]} if project in excluded else
                   {m for r in group for m in passages[r['interval_id']]['motivos']})
        if not reasons:
            continue
        first = group[0]
        raw = first['cadastro_atual_origem_json']
        context = json.loads(raw)
        known = [r for r in group if (r['status_nome'] or '').strip()]
        entries = [r['entrada_status_utc'] for r in group
                   if (r['status_nome'] or '').strip().casefold() == 'entrada']
        evidence = [{k: r[k] for k in ('interval_id', 'ambiente_origem', 'item_id',
                    'ordem_etapa', 'status_nome', 'entrada_status_utc', 'saida_status_utc')}
                    for r in group]
        outputs[QUALITY].append({
            'projeto_id': project, 'projeto_nome': first['projeto_nome'],
            'item_id_viu2': first['item_id_viu2'], 'item_id_globocorp': first['item_id_globocorp'],
            'quantidade_passagens': len(group), 'status_atual': context['status_nome'],
            'cadastro_capturado_em': context['capturado_em'],
            'corte_historico_utc': first['corte_globocorp_utc'],
            'marca': first['cadastro_atual_marca'], 'talento': first['talento_nome_atual'],
            'eh_interveniencia': first['eh_interveniencia'], 'cadastro_atual_json': raw,
            'versao_regra': RULE, 'motivos_json': json.dumps(sorted(reasons)),
            'primeiro_status_conhecido': known[0]['status_nome'] if known else None,
            'primeira_entrada_observada_utc': entries[0] if entries else None,
            'evidencias_passagens_json': json.dumps(evidence, ensure_ascii=False)})
    accepted = {r['projeto_id'] for r in outputs[SLA]}
    if accepted & set(excluded) or accepted | set(excluded) != set(groups):
        raise ValueError('Ciclos: projetos nao reconciliados')
    represented = len(outputs[SLA]) + sum(len(groups[p]) for p in excluded)
    if represented != len(base):
        raise ValueError('Ciclos: passagens nao reconciliadas')
    return outputs, {'rule': VERSION, 'balanced': True,
        'source_projects': len(groups), 'source_passages': len(base),
        'accepted_projects': len(accepted), 'excluded_projects': len(excluded),
        'excluded_passages': sum(len(groups[p]) for p in excluded),
        'destinations': {name: {'rows': len(data), 'projects': len({r['projeto_id'] for r in data})}
                         for name, data in outputs.items()},
        'quality_is_diagnostic': True, 'queue_is_subset': True}
