from copy import deepcopy
from datetime import date, datetime

import pytest
from monday_sla_orcamento.pricing import project
from sls_orcamento_ppd.rules.business_time import BusinessCalendar


def example(labels=None, times=None, calendar=None):
    calendar = calendar or BusinessCalendar("America/Sao_Paulo")
    labels = labels or ["Entrada", "Standby", "Em revisão", "Aguardando Feedback"]
    times = times or ["2026-09-24T13:00:00Z", "2026-09-24T14:00:00Z",
                      "2026-09-24T15:00:00Z", "2026-09-24T18:00:00Z"]
    return [dict(interval_id=str(i), projeto_id="p", ambiente_origem="globocorp",
                 status_nome=label, entrada_status_utc=times[i],
                 saida_status_utc=times[i+1] if i+1 < len(times) else None,
                 elegivel_comparacao=i+1 < len(times),
                 registro_origem_json='{"qualidade_historico":"observed"}',
                 versao_calendario_origem=calendar.version)
            for i, label in enumerate(labels)]


def test_two_clocks_revision_included_pause_excluded_no_mutation():
    rows = example()
    before = deepcopy(rows)
    result = project(rows, BusinessCalendar("America/Sao_Paulo"))
    assert rows == before
    assert result['3']['precificacao_horas_corridas'] == 4
    assert result['3']['precificacao_horas_uteis'] == 3
    assert result['3']['pausas_precificacao_horas_corridas'] == 1
    assert result['3']['janela_precificacao_horas_corridas'] == 5
    assert result['2']['contribuicao_precificacao_horas_uteis'] == 2
    assert result['1']['contribuicao_precificacao_horas_uteis'] is None
    assert sum(v['precificacao_horas_corridas'] is not None for v in result.values()) == 1


@pytest.mark.parametrize('pause', ['Standby', 'Em elaboração - Retorno Marca/Executivo'])
def test_both_pause_types(pause):
    rows = example()
    rows[1]['status_nome'] = pause
    assert project(rows, BusinessCalendar('America/Sao_Paulo'))['3']['precificacao_horas_corridas'] == 4


@pytest.mark.parametrize('terminal', ['Encerrado', 'Declinado Internamente', 'Declinado pelo Mercado'])
def test_terminal_before_delivery_not_an_observed_delivery(terminal):
    rows = example()
    rows[2]['status_nome'] = terminal
    result = project(rows, BusinessCalendar('America/Sao_Paulo'))
    assert result['0']['situacao_ciclo_precificacao'] == 'encerrado_sem_entrega'
    assert all(not r['entrega_precificacao_observada'] for r in result.values())


@pytest.mark.parametrize('fault', ['gap', 'unknown', 'unapproved_pause', 'calendar', 'migration'])
def test_incomplete_evidence_does_not_become_kpi(fault):
    rows = example()
    if fault == 'gap':
        rows[1]['saida_status_utc'] = None
    elif fault == 'unknown':
        rows[1]['status_nome'] = 'Novo status'
    elif fault == 'unapproved_pause':
        rows[1]['elegivel_comparacao'] = False
    elif fault == 'calendar':
        rows[1]['versao_calendario_origem'] = 'other'
    else:
        rows[-1]['ambiente_origem'] = 'viu2'
    result = project(rows, BusinessCalendar('America/Sao_Paulo'))
    assert all(r['precificacao_horas_corridas'] is None for r in result.values())


def test_after_first_feedback_not_counted():
    rows = example()
    extra = {**rows[-1], 'interval_id': '4', 'status_nome': 'Em revisão',
             'entrada_status_utc': '2026-09-25T13:00:00Z'}
    result = project([*rows, extra], BusinessCalendar('America/Sao_Paulo'))
    assert result['4']['ciclo_precificacao_id'] is None
    assert result['3']['precificacao_horas_corridas'] == 4


def test_missing_entrada_never_invented():
    result = project(example()[1:], BusinessCalendar('America/Sao_Paulo'))
    assert all(r['precificacao_horas_corridas'] is None for r in result.values())


@pytest.mark.parametrize('extra', [(), (date(2026, 9, 4),)])
def test_weekend_national_and_extra_holiday(extra):
    calendar = BusinessCalendar('America/Sao_Paulo', extra)
    times = ['2026-09-04T21:00:00Z', '2026-09-08T14:00:00Z']
    rows = example(['Entrada', 'Aguardando Feedback'], times, calendar)
    out = project(rows, calendar)['1']
    assert out['precificacao_horas_corridas'] == 89
    assert out['precificacao_horas_uteis'] == (1 if extra else 2)


def test_zero_useful_is_valid():
    rows = example(['Entrada', 'Aguardando Feedback'],
                   ['2026-09-26T10:00:00Z', '2026-09-26T11:00:00Z'])
    out = project(rows, BusinessCalendar('America/Sao_Paulo'))['1']
    assert out['precificacao_horas_uteis'] == 0
    assert out['entrega_precificacao_observada']


def test_repeated_start_marks_previous_attempt_not_delivered():
    rows = example(['Entrada', 'Entrada', 'Em revisão', 'Aguardando Feedback'])
    out = project(rows, BusinessCalendar('America/Sao_Paulo'))
    assert out['0']['situacao_ciclo_precificacao'] == 'reiniciado_sem_entrega'
    assert out['3']['ciclo_precificacao_id'] == '1'


def test_date_fields_valid():
    out = project(example(), BusinessCalendar('America/Sao_Paulo'))['3']
    assert datetime.fromisoformat(out['fim_precificacao_utc']) > datetime.fromisoformat(out['inicio_precificacao_utc'])


def test_delivery_label_not_trusted_automatically():
    rows = example()
    rows[-1]['registro_origem_json'] = '{}'
    out = project(rows, BusinessCalendar('America/Sao_Paulo'))['3']
    assert out['precificacao_horas_corridas'] is None
    assert out['situacao_ciclo_precificacao'] == 'evidencia_insuficiente'


def test_projection_tampering_blocks_publication():
    from monday_sla_orcamento.consolidation import validate
    from test_estimates import sample

    rows = sample()
    rows[0]['precificacao_horas_corridas'] = 999
    with pytest.raises(ValueError, match='precificacao'):
        validate(rows)


def test_previous_v7_remains_readable():
    from monday_sla_orcamento.consolidation import ANALYSIS_VERSION, fields_for, validate
    from test_estimates import sample

    rows = [{k: v for k, v in r.items() if k in fields_for(ANALYSIS_VERSION)} for r in sample()]
    for r in rows:
        r['versao_contrato'] = ANALYSIS_VERSION
    validate(rows)
