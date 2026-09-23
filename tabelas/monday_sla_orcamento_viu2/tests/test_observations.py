from copy import deepcopy

import pytest
from historico_viu2.observations import build_observations


def event(key, batch=False, **data):
    return {"id": key, "account_id": "1", "created_at": "2026-01-15T12:00:00Z",
            "event": "batch_change_pulses_column_value" if batch else "update_column_value",
            "data": {"column_id": "status_19", "action_record_uuid": "a", **data}}


def build(records):
    return build_observations(records, account_id="1", board_id="b")


def test_batch_and_individual_not_double_counted_and_missing_item_preserved():
    raw = [event("b", True, pulse_ids=[1, 2], value={"index": 0}),
           event("i", pulse_id=1, value={"label": {"index": 0}})]
    original = deepcopy(raw)
    report = build(raw)
    assert len(report["observations"]) == 2
    assert len(report["observations"][0]["sources"]) == 2
    assert report["summary"]["batch_only_explicit"] == 1
    assert raw == original


def test_unknown_batch_does_not_erase_known_individual():
    report = build([event("b", True, pulse_ids=[1, 2]),
                    event("i", pulse_id=1, value={"index": 7})])
    assert report["observations"][0]["status_index"] == "7"
    assert report["observations"][1]["status_index"] is None
    assert report["summary"]["batch_only_unknown"] == 1


def test_conflict_cannot_choose_arbitrary_value():
    report = build([event("b", True, pulse_ids=[1], value={"index": 1}),
                    event("i", pulse_id=1, value={"index": 7})])
    assert report["observations"][0]["status_index"] is None
    assert report["observations"][0]["review_reasons"] == ["unknown_or_conflicting_status"]


def test_unknown_individual_not_replaced_by_batch():
    report = build([event("b", True, pulse_ids=[1], value={"index": 1}), event("i", pulse_id=1)])
    assert report["observations"][0]["status_index"] is None


def test_missing_uuid_does_not_merge_by_status_or_time():
    report = build([event("i1", pulse_id=1, action_record_uuid=None, value={"index": 0}),
                    event("i2", pulse_id=1, action_record_uuid=None, value={"index": 0})])
    assert len(report["observations"]) == 2
    assert report["summary"]["review_reasons"]["missing_action_uuid"] == 2


def test_time_conflict_and_order_independence():
    raw = [event("i1", pulse_id=1, value={"index": 0}),
           event("i2", pulse_id=1, value={"index": 0})]
    raw[1]["created_at"] = "2026-01-15T13:00:00Z"
    assert build(raw) == build(list(reversed(raw)))
    assert build(raw)["observations"][0]["event_at_utc"] is None


def test_fail_closed_on_duplicates_or_account_mismatch():
    record = event("i", pulse_id=1)
    with pytest.raises(ValueError):
        build([record, record])
    record["account_id"] = "2"
    with pytest.raises(ValueError):
        build([record])
