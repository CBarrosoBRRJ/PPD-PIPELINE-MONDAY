from copy import deepcopy

import pytest
from monday_sla_orcamento.analysis_duration import FIELDS, project
from monday_sla_orcamento.consolidation import validate
from test_estimates import sample


def test_estimate_selected_without_changing_official_fields():
    row = sample()[0]
    before = deepcopy(row)
    result = project(row)
    assert row == before
    assert result["origem_duracao_analise"] == "estimada"
    assert result["duracao_analise_horas"] == row["duracao_estimada_horas"]
    assert result["duracao_analise_horas_uteis"] == row["duracao_estimada_horas_uteis"]
    assert row["sla_etapa_horas_uteis"] is None


def test_observed_zero_has_priority():
    row = sample()[0]
    row.update(elegivel_comparacao=True, sla_etapa_horas_uteis=0.0, duracao_horas=1.0)
    result = project(row)
    assert result["origem_duracao_analise"] == "observada_validada"
    assert result["duracao_analise_horas_uteis"] == 0.0
    assert result["duracao_analise_horas"] == 1.0


@pytest.mark.parametrize("terminal", [True, None])
def test_terminal_or_unknown_does_not_accrue(terminal):
    row = sample()[0]
    row["status_terminal"] = terminal
    assert project(row)["duracao_analise_horas"] is None


def test_unapproved_observed_duration_not_promoted():
    row = sample()[0]
    row.update(saida_status_utc="2026-09-02T10:00:00Z", duracao_horas=24, duracao_horas_uteis=8)
    result = project(row)
    assert result["origem_duracao_analise"] == "indisponivel"
    assert result["duracao_analise_horas_uteis"] is None


@pytest.mark.parametrize("field", list(FIELDS))
def test_tampered_projection_blocks_publication(field):
    rows = sample()
    rows[0][field] = 999 if FIELDS[field][0] == "FLOAT" else "invalid"
    with pytest.raises(ValueError, match="analise"):
        validate(rows)
