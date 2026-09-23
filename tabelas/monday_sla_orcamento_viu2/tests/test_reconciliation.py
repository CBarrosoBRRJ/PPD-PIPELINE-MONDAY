from copy import deepcopy

import pytest
from historico_viu2.reconciliation import audit_status_batches, profile_batch_coverage


def event(key, batch=False, **data):
    return {"id": key, "account_id": "1",
            "event": "batch_change_pulses_column_value" if batch else "update_column_value",
            "data": {"column_id": "status_19", "action_record_uuid": "action", **data}}


def test_reconcile_each_item_not_merely_action():
    records = [event("batch", True, pulse_ids=[1, 2], value={"index": 7}),
               event("individual", pulse_id=1, value={"label": {"index": 7}})]
    original = deepcopy(records)
    report = audit_status_batches(records)
    assert report["categories"] == {"same_action_item_and_status": 1, "missing_individual_with_value": 1}
    assert report["review_required"]
    assert records == original


def test_conflicting_status_cannot_be_considered_covered():
    report = audit_status_batches([event("b", True, pulse_ids=[1], value={"index": 7}),
                                   event("i", pulse_id=1, value={"index": 8})])
    assert report["categories"] == {"status_conflict_or_unknown": 1}


def test_missing_value_is_not_assumed_to_mean_empty_status():
    report = audit_status_batches([event("b", True, pulse_ids=[1])])
    assert report["categories"] == {"missing_individual_without_value": 1}


def test_duplicate_events_rejected():
    record = event("b", True, pulse_ids=[1])
    with pytest.raises(ValueError, match="repetido"):
        audit_status_batches([record, record])


def test_profile_distinguishes_absent_null_and_known_without_inference():
    records = [event("b1", True, pulse_ids=[1, 2]),
               event("b2", True, pulse_ids=[1], value=None),
               event("b3", True, pulse_ids=[3], value={"index": 0})]
    original = deepcopy(records)
    profile = profile_batch_coverage(records, [1, 3])
    assert profile["batch_value_shapes"] == {
        "value_field_absent": 1, "value_explicit_null": 1, "explicit_status_index": 1}
    assert profile["items_without_individual_counterpart"] == 3
    assert profile["items_without_individual_counterpart_in_context"] == 2
    assert profile["review_categories"]["missing_individual_without_value"]["distinct_items"] == 2
    assert profile["release_ready"] is False
    assert records == original


def test_profile_individual_evidence_does_not_fill_unknown_batch():
    records = [event("b", True, pulse_ids=[1]), event("i", pulse_id=1, value={"index": 0})]
    profile = profile_batch_coverage(records, [1])
    assert profile["items_without_individual_counterpart"] == 0
    assert profile["review_categories"]["individual_present_batch_value_unknown"]["distinct_items"] == 1
    assert profile["release_ready"] is False
