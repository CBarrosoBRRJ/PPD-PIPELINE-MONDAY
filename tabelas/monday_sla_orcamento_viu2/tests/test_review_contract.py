from copy import deepcopy

import pytest
from historico_viu2.review_contract import project_review, schema, validate
from sls_orcamento_ppd.rules.business_time import BusinessCalendar


def candidate(quality="observed_closed_candidate"):
    closed = quality == "observed_closed_candidate"
    return {"calendar": {"version": BusinessCalendar("America/Sao_Paulo").version}, "passages": [{
        "source_account_id": "5890468", "source_board_id": "18393336134", "source_item_id": "123",
        "tipo_input_verificado": True, "tipo_input": None,
        "entrada_status_utc": "2026-01-19T13:00:00+00:00",
        "saida_status_utc": "2026-01-19T15:00:00+00:00" if closed else None,
        "status_index": "0", "quality": quality, "duracao_horas": 2 if closed else None,
        "duracao_horas_uteis": 2 if closed else None, "status_nome": None, "projeto_nome": None,
        "attribute_source": "unavailable", "schema_event_ids_during_passage": [],
        "marca_original": None, "talento_original": None, "cadastro_referencia_utc": None,
        "status_label_quality": "historical_label_unavailable", "observed_visit_number": 1,
        "supporting_event_ids": ["1"], "end_event_ids": ["2"] if closed else [],
    }]}


@pytest.mark.parametrize("verified", [False, None])
def test_unverified_input_excluded_not_treated_as_blank(verified):
    source = candidate()
    source["passages"][0]["tipo_input_verificado"] = verified
    assert project_review(source) == []


def test_verified_blank_allowed():
    assert len(project_review(candidate())) == 1


@pytest.mark.parametrize("quality", ["observed_closed_candidate", "no_observed_exit", "interrupted_by_evidence_gap"])
def test_known_start_unknown_duration_represented_without_approval(quality):
    source = candidate(quality)
    original = deepcopy(source)
    rows = project_review(source)
    validate(rows)
    assert rows[0]["entrada_status_utc"] is not None
    assert rows[0]["elegivel_comparacao"] is False
    assert rows[0]["status_nome"] is None
    assert set(rows[0]) == {f["name"] for f in schema()}
    assert source == original


@pytest.mark.parametrize("field,value", [
    ("duracao_horas", 9), ("duracao_horas_uteis", 1), ("elegivel_comparacao", True),
    ("item_id", 456), ("ordem_etapa", 2), ("eventos_saida_json", "[]"),
    ("entrada_status_local", "2026-01-19T00:00:00"), ("versao_calendario", "other"),
    ("duracao_horas", float("nan")), ("board_id", True),
])
def test_corruption_rejected(field, value):
    rows = project_review(candidate())
    rows[0][field] = value
    with pytest.raises(ValueError):
        validate(rows)


def test_unknown_duration_cannot_be_zero_and_duplicates_rejected():
    rows = project_review(candidate("no_observed_exit"))
    with pytest.raises(ValueError):
        validate(rows + rows)
    rows[0]["duracao_horas"] = 0
    with pytest.raises(ValueError):
        validate(rows)
