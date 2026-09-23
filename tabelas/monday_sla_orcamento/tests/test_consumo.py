from copy import deepcopy

import pytest
from monday_sla_orcamento.consumo import project
from test_kpi_etapa import candidate


def test_safe_metric_and_no_mutation():
    row, calendar = candidate()
    original = deepcopy(row)
    projected = project(row, calendar)
    assert projected["sla_etapa_horas_uteis"] == 8
    assert projected["classificacao_consumo"] == "aprovado_kpi_etapa"
    assert projected["motivos_inelegibilidade_kpi_json"] == "[]"
    assert row == original


@pytest.mark.parametrize("changes,category", [
    ({"status_terminal": True}, "encerramento_observado"),
    ({"status_terminal": None}, "evidencia_insuficiente"),
    ({"pendencias_json": '["status_schema_review_pending"]'}, "evidencia_insuficiente"),
    ({"saida_status_utc": None, "situacao_sla_registro": "sem_saida_observada_nao_comprova_abandono"}, "sem_saida_observada"),
])
def test_noneligible_metric_is_null(changes, category):
    row, calendar = candidate()
    row.update(changes)
    projected = project(row, calendar)
    assert projected["sla_etapa_horas_uteis"] is None
    assert projected["classificacao_consumo"] == category
    assert projected["motivos_inelegibilidade_kpi_json"] != "[]"


def test_real_zero_not_null():
    row, calendar = candidate()
    row.update(entrada_status_utc="2026-09-16T16:00:00Z", saida_status_utc="2026-09-16T17:00:00Z",
               duracao_horas=1.0, duracao_horas_uteis=0.0)
    assert project(row, calendar)["sla_etapa_horas_uteis"] == 0.0


@pytest.mark.parametrize("field,value", [("sla_etapa_horas_uteis", 999), ("classificacao_consumo", "aprovado_kpi_etapa"),
                                       ("versao_regra_kpi", "other"), ("motivos_inelegibilidade_kpi_json", "[]")])
def test_contract_rejects_tampering(field, value):
    from monday_sla_orcamento.consolidation import build, validate
    from test_consolidation import inputs
    rows, _ = build(*inputs())
    rows[0][field] = value
    with pytest.raises(ValueError, match="consumo"):
        validate(rows)
