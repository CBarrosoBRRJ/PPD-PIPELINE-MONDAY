from copy import deepcopy
from datetime import UTC, datetime

import pytest
from historico_viu2.enrichment import enrich_passages


def setup(label="Antigo"):
    event = {"account_id": "1", "id": "e", "event": "update_column_value",
             "created_at": "2026-01-19T13:00:00Z", "data": {"pulse_id": "i", "column_id": "status_19",
             "value": {"label": {"index": 0, "text": label}}}}
    candidate = {"passages": [{"source_account_id": "1", "source_board_id": "b", "source_item_id": "i",
                 "status_index": "0", "entrada_status_utc": "2026-01-19T13:00:00Z",
                 "saida_status_utc": None, "supporting_event_ids": ["e"]}], "gaps": [], "calendar": {}}
    return event, candidate


def test_event_label_not_replaced_with_current_label_and_context_dated():
    event, candidate = setup()
    original = deepcopy(candidate)
    snap = {"board_id": "b", "item_id": "i", "item_name": "Projeto",
            "snapshot_at": datetime(2026, 9, 21, tzinfo=UTC)}
    result = enrich_passages(candidate, [event], [snap], {"0": "Atual"})
    row = result["passages"][0]
    assert row["status_nome"] == "Antigo"
    assert row["status_nome_no_cadastro"] == "Atual"
    assert row["cadastro_referencia_utc"].startswith("2026-09-21")
    assert not row["sla_approved"]
    assert candidate == original


def test_missing_event_label_or_context_remain_null():
    event, candidate = setup(None)
    row = enrich_passages(candidate, [event], [], {"0": "Atual"})["passages"][0]
    assert row["status_nome"] is None
    assert row["projeto_nome"] is None
    assert row["attribute_source"] == "unavailable"


def test_later_label_cannot_fill_start_and_schema_is_only_a_flag():
    event, candidate = setup()
    event["created_at"] = "2026-01-20T13:00:00Z"
    schema = {"account_id": "1", "id": "s", "event": "change_column_settings",
              "created_at": "2026-01-20T13:00:00Z", "data": {"column_id": "status_19"}}
    row = enrich_passages(candidate, [event, schema], [], {})["passages"][0]
    assert row["status_nome"] is None
    assert row["schema_event_ids_during_passage"] == ["s"]


def test_lineage_from_other_item_rejected():
    event, candidate = setup()
    event["data"]["pulse_id"] = "other"
    with pytest.raises(ValueError):
        enrich_passages(candidate, [event], [], {})


def closing_case():
    event, candidate = setup(None)
    end = deepcopy(event)
    end.update(id="end", created_at="2026-01-20T13:00:00Z")
    end["data"]["previous_value"] = {"label": {"index": 0, "text": "Histórico"}}
    end["data"]["value"] = {"label": {"index": 8, "text": "Encerrado"}}
    candidate["passages"][0].update(
        saida_status_utc=end["created_at"], end_event_ids=["end"])
    return event, end, candidate


def test_exact_exit_previous_label_recovers_without_changing_dates_or_source():
    event, end, candidate = closing_case()
    original = deepcopy(candidate)
    row = enrich_passages(candidate, [event, end], [], {"0": "Atual"})["passages"][0]
    assert row["status_nome"] == "Histórico"
    assert row["status_label_quality"] == "label_observed_at_exit_previous_value"
    assert row["label_exit_evidence_ids"] == ["end"]
    assert candidate == original
    assert not row["sla_approved"]


@pytest.mark.parametrize("mutation", ["time", "index", "blank", "schema", "conflict"])
def test_exit_recovery_does_not_guess(mutation):
    event, end, candidate = closing_case()
    records = [event, end]
    if mutation == "time":
        end["created_at"] = "2026-01-20T13:00:01Z"
    elif mutation == "index":
        end["data"]["previous_value"]["label"]["index"] = 4
    elif mutation == "blank":
        end["data"]["previous_value"]["label"]["text"] = " "
    elif mutation == "schema":
        records.append({"account_id": "1", "id": "schema", "event": "change_column_settings",
                        "created_at": "2026-01-19T14:00:00Z", "data": {"column_id": "status_19"}})
    else:
        other = deepcopy(end)
        other["id"] = "other"
        other["data"]["previous_value"]["label"]["text"] = "Outro nome"
        records.append(other)
        candidate["passages"][0]["end_event_ids"].append("other")
    row = enrich_passages(candidate, records, [], {})["passages"][0]
    assert row["status_nome"] is None


@pytest.mark.parametrize("field,value", [("pulse_id", "other"), ("board_id", "other"),
                                        ("column_id", "other")])
def test_foreign_exit_lineage_blocks_batch(field, value):
    event, end, candidate = closing_case()
    end["data"][field] = value
    with pytest.raises(ValueError, match="Linhagem de saída"):
        enrich_passages(candidate, [event, end], [], {})


def test_observed_start_label_is_not_overwritten_by_exit():
    event, end, candidate = closing_case()
    event["data"]["value"]["label"]["text"] = "Nome inicial"
    row = enrich_passages(candidate, [event, end], [], {})["passages"][0]
    assert row["status_nome"] == "Nome inicial"
