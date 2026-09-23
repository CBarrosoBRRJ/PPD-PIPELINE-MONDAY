from copy import deepcopy

import pytest
from monday_sla_orcamento.consolidation import build, validate
from monday_sla_orcamento.estimates import FIELDS, project
from sls_orcamento_ppd.rules.business_time import BusinessCalendar
from test_consolidation import inputs


def sample():
    old, new, mapping = inputs()
    old[0].update(saida_status_utc=None, saida_status_local=None, duracao_horas=None, duracao_horas_uteis=None)
    return build(old, new, mapping)[0]


def test_estimate_preserves_observations_and_kpi():
    rows = sample()
    original = deepcopy(rows)
    result = project(rows, BusinessCalendar("America/Sao_Paulo"))
    assert rows == original
    assert result[rows[0]["interval_id"]]["duracao_estimada_horas"] == 72
    assert rows[0]["saida_status_utc"] is None
    assert rows[0]["sla_etapa_horas_uteis"] is None
    assert rows[0]["continuidade_validada"] is False
    assert rows[1]["saida_estimada_utc"] is None


@pytest.mark.parametrize("fault", ["terminal", "unknown", "existing_exit", "same_origin", "same_status",
                                   "unknown_identity", "after_cut", "overlap_flag"])
def test_no_estimate_when_unsupported(fault):
    rows = sample()
    if fault == "terminal":
        rows[0]["status_terminal"] = True
    elif fault == "unknown":
        rows[1]["status_terminal"] = None
    elif fault == "existing_exit":
        rows[0]["saida_status_utc"] = rows[1]["entrada_status_utc"]
    elif fault == "same_origin":
        rows[1].update(ambiente_origem="viu2", item_id=rows[1]["item_id_viu2"])
    elif fault == "same_status":
        rows[1]["status_nome"] = rows[0]["status_nome"]
    elif fault == "unknown_identity":
        rows[0]["qualidade_identidade"] = "pending"
    elif fault == "after_cut":
        rows[0]["corte_globocorp_utc"] = rows[0]["entrada_status_utc"]
    else:
        rows[0]["pendencias_json"] = '["sobreposicao_temporal_duracao_bloqueada"]'
    result = project(rows, BusinessCalendar("America/Sao_Paulo"))
    assert all(r["saida_estimada_utc"] is None for r in result.values())


@pytest.mark.parametrize("field", list(FIELDS))
def test_forged_estimate_blocked(field):
    rows = sample()
    rows[0][field] = None if FIELDS[field][1] is False else "incorrect"
    with pytest.raises(ValueError):
        validate(rows)


def test_no_next_passage_and_no_cross_project_estimate():
    rows = sample()[:1]
    assert project(rows, BusinessCalendar("America/Sao_Paulo"))[rows[0]["interval_id"]]["saida_estimada_utc"] is None


def test_weekend_zero_is_valid_estimate_not_official_zero():
    rows = sample()
    rows[0]["entrada_status_utc"] = "2026-09-19T12:00:00Z"
    rows[1]["entrada_status_utc"] = "2026-09-20T12:00:00Z"
    for row in rows:
        row["corte_globocorp_utc"] = "2026-09-21T03:00:00Z"
    estimate = project(rows, BusinessCalendar("America/Sao_Paulo"))[rows[0]["interval_id"]]
    assert estimate["duracao_estimada_horas_uteis"] == 0
    assert estimate["saida_estimada_local"] == "2026-09-20T09:00:00.000000"
    assert rows[0]["sla_etapa_horas_uteis"] is None


def test_input_order_does_not_change_estimate():
    rows = sample()
    calendar = BusinessCalendar("America/Sao_Paulo")
    assert project(rows, calendar) == project(list(reversed(rows)), calendar)


def test_observed_exit_replaces_hypothesis_on_next_rebuild():
    rows = sample()
    calendar = BusinessCalendar("America/Sao_Paulo")
    assert project(rows, calendar)[rows[0]["interval_id"]]["saida_estimada_utc"] is not None
    rows[0]["saida_status_utc"] = rows[1]["entrada_status_utc"]
    result = project(rows, calendar)[rows[0]["interval_id"]]
    assert result["metodo_estimativa"] == "nao_aplicavel"
    assert all(result[k] is None for k, (_, required) in FIELDS.items() if not required)
