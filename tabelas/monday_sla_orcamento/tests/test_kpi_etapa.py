import json
from copy import deepcopy

import pytest
from monday_sla_orcamento.kpi_etapa import decision
from sls_orcamento_ppd.rules.business_time import BusinessCalendar


def candidate():
    calendar = BusinessCalendar("America/Sao_Paulo")
    return {
        "ambiente_origem": "viu2", "status_terminal": False, "status_nome": "Entrada",
        "situacao_sla_registro": "passagem_com_saida_observada",
        "versao_calendario_origem": calendar.version,
        "entrada_status_utc": "2026-09-16T13:00:00Z", "saida_status_utc": "2026-09-16T22:00:00Z",
        "duracao_horas": 9.0, "duracao_horas_uteis": 8.0,
        "pendencias_json": '["validacao_negocio_pendente", "migration_boundary_pending"]',
        "registro_origem_json": json.dumps({
            "situacao_passagem": "observed_closed_candidate", "qualidade_rotulo": "label_observed_at_start",
            "eventos_suporte_json": '["start"]', "eventos_saida_json": '["end"]',
        }),
    }, calendar


def test_completed_stage_does_not_approve_global_continuity_or_mutate():
    row, calendar = candidate()
    before = deepcopy(row)
    result = decision(row, calendar)
    assert result["elegivel_kpi_etapa_candidato"]
    assert not result["continuidade_entre_ambientes_aprovada"]
    assert row == before


@pytest.mark.parametrize("issue", ["status_schema_review_pending", "interrupted_by_evidence_gap",
                                  "sobreposicao_temporal_duracao_bloqueada", "future_unknown_issue"])
def test_unresolved_evidence_blocks(issue):
    row, calendar = candidate()
    row["pendencias_json"] = json.dumps([issue])
    assert not decision(row, calendar)["elegivel_kpi_etapa_candidato"]


@pytest.mark.parametrize("field,value", [
    ("status_terminal", True), ("status_terminal", None), ("status_nome", " "),
    ("saida_status_utc", None), ("duracao_horas_uteis", None), ("duracao_horas_uteis", 7),
    ("duracao_horas", float("nan")), ("versao_calendario_origem", "unknown"),
])
def test_incomplete_or_inconsistent_not_eligible(field, value):
    row, calendar = candidate()
    row[field] = value
    assert not decision(row, calendar)["elegivel_kpi_etapa_candidato"]


def test_zero_working_hours_is_not_missing():
    row, calendar = candidate()
    row.update(entrada_status_utc="2026-09-16T16:00:00Z", saida_status_utc="2026-09-16T17:00:00Z",
               duracao_horas=1.0, duracao_horas_uteis=0.0)
    assert decision(row, calendar)["elegivel_kpi_etapa_candidato"]


@pytest.mark.parametrize("field,value", [("eventos_saida_json", "[]"),
                                        ("qualidade_rotulo", "conflicting_start_labels")])
def test_source_evidence_required(field, value):
    row, calendar = candidate()
    source = json.loads(row["registro_origem_json"])
    source[field] = value
    row["registro_origem_json"] = json.dumps(source)
    assert not decision(row, calendar)["elegivel_kpi_etapa_candidato"]


def test_globocorp_requires_source_eligibility():
    row, calendar = candidate()
    row["ambiente_origem"] = "globocorp"
    for eligible in (False, True):
        row["registro_origem_json"] = json.dumps({"qualidade_historico": "observed", "elegivel_comparacao": eligible})
        assert decision(row, calendar)["elegivel_kpi_etapa_candidato"] == eligible


def test_builder_applies_policy_and_validator_rejects_forged_approval():
    from monday_sla_orcamento.consolidation import build, validate
    from test_consolidation import inputs

    old, new, mapping = inputs()
    old[0].update(qualidade_rotulo="label_observed_at_start", eventos_suporte_json='["start"]',
                  eventos_saida_json='["end"]', versao_calendario=BusinessCalendar("America/Sao_Paulo").version)
    rows, _ = build(old, new, mapping, old_inputs={(18393336134, 1): None})
    assert rows[0]["elegivel_comparacao"] is True
    assert rows[0]["validacao_negocio"] == "aprovado_etapa_origem_v1"
    assert rows[1]["elegivel_comparacao"] is False
    assert all(not r["continuidade_validada"] for r in rows)
    rows[1]["elegivel_comparacao"] = True
    with pytest.raises(ValueError, match="elegibilidade"):
        validate(rows)
    unchecked, _ = build(old, new, mapping)
    assert not any(r["elegivel_comparacao"] for r in unchecked)
