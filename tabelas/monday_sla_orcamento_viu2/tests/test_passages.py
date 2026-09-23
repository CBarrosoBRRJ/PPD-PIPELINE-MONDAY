from copy import deepcopy

import pytest
from historico_viu2.passages import build_passages


def observation(key, hour, status, **extra):
    return {"source_account_id": "1", "source_board_id": "b", "source_item_id": "i",
            "operation_kind": "event", "operation_id": key, "status_index": status,
            "event_at_utc": f"2026-01-19T{hour}:00:00Z", "review_reasons": [],
            "sources": [{"event_id": key}], **extra}


def build(*rows):
    return build_passages({"observations": list(rows)})


def test_observed_change_closes_but_last_is_not_extended_to_today():
    report = build(observation("1", "13", "a"), observation("2", "15", "b"))
    first, last = report["passages"]
    assert first["duracao_horas"] == first["duracao_horas_uteis"] == 2
    assert last["duracao_horas"] is None
    assert last["saida_status_utc"] is None
    assert not first["sla_approved"]


def test_gap_interrupts_and_does_not_bridge_even_same_status():
    report = build(observation("1", "13", "a"), observation("2", "14", None),
                   observation("3", "15", "a"), observation("4", "16", "b"))
    assert len(report["passages"]) == 3
    assert report["passages"][0]["duracao_horas"] is None
    assert report["passages"][0]["quality"] == "interrupted_by_evidence_gap"
    assert report["passages"][1]["duracao_horas"] == 1
    assert report["summary"]["gap_records"] == 1


def test_same_status_supports_one_passage_and_preserves_sources():
    report = build(observation("1", "13", "a"), observation("2", "14", "a"),
                   observation("3", "15", "b"))
    assert report["passages"][0]["supporting_event_ids"] == ["1", "2"]
    assert report["passages"][0]["duracao_horas"] == 2


def test_simultaneous_conflict_never_arbitrarily_ordered():
    report = build(observation("1", "13", "a"), observation("2", "14", "b"),
                   observation("3", "14", "c"))
    assert report["passages"][0]["duracao_horas"] is None
    assert report["summary"]["gap_records"] == 1


def test_unlocated_gap_quarantines_only_affected_source_item():
    report = build(observation("1", "13", "a", event_at_utc=None),
                   observation("2", "14", "b"),
                   observation("3", "13", "a", source_item_id="other"),
                   observation("4", "15", "b", source_item_id="other"))
    assert report["summary"]["passages_with_duration"] == 1
    assert report["gaps"][0]["reason"] == "unlocated_timestamp_gap"


def test_deterministic_no_mutation_and_duplicates_rejected():
    rows = [observation("1", "13", "a"), observation("2", "15", "b")]
    original = deepcopy(rows)
    assert build(*rows) == build(*reversed(rows))
    assert rows == original
    with pytest.raises(ValueError):
        build(rows[0], rows[0])
