from monday_log_viu2.structured import project


def test_projection_keeps_raw_values_and_does_not_fabricate_bad_fields():
    row = {"id": "1", "account_id": "old", "user_id": "2", "entity": "pulse",
           "event": "update_column_value", "created_at": "invalid",
           "data": '{"pulse_id":true,"column_id":"status_19","value":{"unknown":null}}'}
    result = project(row, {"captured_at": "2026-09-21T00:00:00Z"},
                     {"source": "viu2", "account_id": "old", "board_id": "123"},
                     "page.json.gz", "archive")
    assert result["data_raw"] == row["data"]
    assert result["event_at_raw"] == "invalid"
    assert result["event_at_utc"] is None
    assert result["item_id"] is None
    assert result["column_id"] == "status_19"
    assert result["parse_warnings"] == "unparsed_timestamp,unparsed_item_id"
