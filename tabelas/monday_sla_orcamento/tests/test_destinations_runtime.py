import copy
import json

import pytest
from monday_sla_orcamento.consolidation import build as consolidate
from monday_sla_orcamento.current_context import ATTRIBUTES
from monday_sla_orcamento.destination_publication import fingerprint, normalize
from monday_sla_orcamento.destinations import QUALITY, QUEUE, SLA, build
from test_consolidation import inputs


def candidate(kind='queue', current='Entrada'):
    old, new, mapping = inputs()
    old[0].update(saida_status_utc=None, saida_status_local=None,
                  duracao_horas=None, duracao_horas_uteis=None)
    new[0].update(entrada_status_utc=None, entrada_status_local=None,
                  qualidade_historico='initial_inferred')
    if kind == 'quality':
        old[0]['status_nome'] = 'Em revisão'
    if kind == 'sla':
        old[0].update(saida_status_utc='2026-09-01T11:00:00Z',
                      saida_status_local='2026-09-01T08:00:00',
                      duracao_horas=1.0, duracao_horas_uteis=0.0)
        following = copy.deepcopy(old[0])
        following.update(interval_id='old2', ordem_etapa=2, status_nome='Aguardando Feedback',
                         entrada_status_utc='2026-09-01T11:00:00Z',
                         entrada_status_local='2026-09-01T08:00:00',
                         saida_status_utc=None, saida_status_local=None,
                         duracao_horas=None, duracao_horas_uteis=None)
        old.append(following)
    context = {**dict.fromkeys(ATTRIBUTES), 'board_id': 18429499488, 'item_id': 2,
               'capturado_em': '2026-09-05T12:00:00.000000+00:00', 'status_nome': current,
               'versao_contrato': 'board-snapshot-v1', 'talentos_exclusivos_json': '["Pessoa"]'}
    return consolidate(old, new, mapping, old_inputs={(18393336134, 1): None},
                       current_context=[context])[0]


@pytest.mark.parametrize(('kind', 'name'), [('queue', QUEUE), ('quality', QUALITY), ('sla', SLA)])
def test_runtime_projection_contract_and_reconciliation(kind, name):
    rows = candidate(kind)
    before = copy.deepcopy(rows)
    outputs, report = build(rows)
    assert report['balanced'] and report['source_projects'] == 1
    assert outputs[name] and all(not v for k, v in outputs.items() if k != name)
    assert rows == before
    assert fingerprint(name, outputs[name]) == fingerprint(name, normalize(name, outputs[name]))


def test_queue_has_real_waiting_time_and_calendar():
    outputs, _ = build(candidate())
    queue = outputs[QUEUE][0]
    assert 0 <= queue['espera_horas_uteis'] <= queue['espera_horas_corridas']
    assert queue['versao_calendario'].startswith('work-v1:')


def test_stale_queue_routes_to_quality_and_reenters_after_correction():
    first, _ = build(candidate(current='Encerrado'))
    assert 'entrada_isolada_diverge_cadastro_atual' in json.loads(first[QUALITY][0]['motivos_json'])
    second, _ = build(candidate())
    assert second[QUEUE] and not second[QUALITY]


def test_actual_observed_direct_feedback_stays_in_sla():
    outputs, _ = build(candidate('sla'))
    assert len(outputs[SLA]) == 2 and not outputs[QUALITY]


def test_invalid_duration_blocks_contract():
    outputs, _ = build(candidate())
    outputs[QUEUE][0]['espera_horas_uteis'] = float('nan')
    with pytest.raises(ValueError):
        normalize(QUEUE, outputs[QUEUE])
