from copy import deepcopy

import pytest
from historico_viu2.reconciliation import profile_item_review


def row(key, event, **data):
    return {"id": key, "account_id": "1", "event": event,
            "data": {"column_id": "status_19", "action_record_uuid": "a", **data}}


def test_groups_preserve_evidence_and_do_not_approve_sla():
    records = [row("i", "update_column_value", pulse_id=1, value={"index": 0}),
               row("b", "batch_change_pulses_column_value", pulse_ids=[2, 4])]
    original = deepcopy(records)
    report = profile_item_review(records, [1, 2, 3], account_id="1", board_id="b")
    items = {r["source_item_id"]: r for r in report["items"]}
    assert items["1"]["triage_group"] == "individual_evidence_no_pending_batch"
    assert items["2"]["triage_group"] == "batch_review_required"
    assert items["3"]["triage_group"] == "no_individual_status_evidence"
    assert items["4"]["in_current_context"] is False
    assert report["summary"]["items_outside_current_context"] == 1
    assert not any(r["sla_approved"] for r in items.values())
    assert records == original


def test_unknown_batch_kept_for_review_even_with_individual():
    records = [row("i", "update_column_value", pulse_id=1, value={"index": 0}),
               row("b", "batch_change_pulses_column_value", pulse_ids=[1])]
    report = profile_item_review(records, [1], account_id="1", board_id="b")
    assert report["items"][0]["batch_review_reasons"] == {
        "individual_present_batch_value_unknown": 1}


def test_account_and_duplicate_validation():
    record = row("i", "update_column_value", pulse_id=1)
    with pytest.raises(ValueError):
        profile_item_review([record], [], account_id="2", board_id="b")
    with pytest.raises(ValueError):
        profile_item_review([record, record], [], account_id="1", board_id="b")


def test_context_only_never_approved():
    report = profile_item_review([], [1, 1], account_id="1", board_id="b")
    assert report["summary"]["items"] == 1
    assert report["summary"]["release_ready"] is False
