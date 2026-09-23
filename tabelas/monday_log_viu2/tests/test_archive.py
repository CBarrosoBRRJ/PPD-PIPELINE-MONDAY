import gzip
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from monday_log_viu2.archive import BoardArchive
from sls_orcamento_ppd.utils.time import iso, parse_timestamp

START = datetime(2026, 9, 1, tzinfo=UTC)


class FakeClient:
    settings = SimpleNamespace(monday_board_id=123, monday_api_version="2026-04")

    def __init__(self, rows):
        self.rows = rows
        self.calls = 0

    def query(self, query, variables):
        self.calls += 1
        if "me {" in query:
            return {"me": {"account": {"id": "account-old"}}}
        if "columns {" in query:
            return {"boards": [{"id": "123", "created_at": iso(START), "columns": []}]}
        start, end = parse_timestamp(variables["from"]), parse_timestamp(variables["to"])
        rows = [r for r in self.rows if start <= parse_timestamp(r["created_at"]) <= end]
        offset = (variables["page"] - 1) * variables["limit"]
        return {"boards": [{"activity_logs": rows[offset:offset + variables["limit"]]}]}


def events():
    return [
        {"id": str(i), "account_id": "account-old", "event": "update_column_value",
         "data": '{"column_id":"any_column","private":"preserve verbatim"}',
         "created_at": iso(START + timedelta(seconds=i)), "user_id": "99", "entity": "pulse"}
        for i in (2, 4, 6, 8)
    ]


def test_saturated_windows_split_and_keep_all_events_without_status_filter(tmp_path):
    client = FakeClient(events())
    archive = BoardArchive(client, tmp_path, "viu2", limit=2, split_at=4)
    archive.window(START, START + timedelta(seconds=10))
    assert len(archive.windows) == 2
    assert archive.verify_events()["unique_events"] == 4
    assert len(archive.inventory) > len(archive.accepted)
    for name in archive.inventory:
        envelope = json.loads(gzip.decompress((tmp_path / name).read_bytes()))
        assert "column_ids" not in envelope["request"]["query"]
        assert "Authorization" not in envelope
    calls = client.calls
    resumed = BoardArchive(client, tmp_path, "viu2", limit=2, split_at=4)
    resumed.window(START, START + timedelta(seconds=10))
    assert client.calls == calls
    assert resumed.verify_events()["unique_events"] == 4


def test_integrity_failure_does_not_refetch_or_overwrite(tmp_path):
    client = FakeClient(events())
    archive = BoardArchive(client, tmp_path, "viu2")
    archive.window(START, START + timedelta(seconds=10))
    target = tmp_path / archive.accepted[0]
    target.write_bytes(b"corrupted")
    calls = client.calls
    with pytest.raises(ValueError, match="integridade"):
        BoardArchive(client, tmp_path, "viu2").window(START, START + timedelta(seconds=10))
    assert target.read_bytes() == b"corrupted"
    assert client.calls == calls


def test_wrong_account_stops_before_board_query_and_marks_incomplete(tmp_path):
    client = FakeClient([])
    with pytest.raises(ValueError, match="Conta autenticada"):
        BoardArchive(client, tmp_path, "viu2").run("another-account")
    assert client.calls == 1
    assert json.loads((tmp_path / "manifest.json").read_text())["status"] == "incomplete"


def test_unresolvable_saturation_is_never_marked_complete(tmp_path):
    client = FakeClient([dict(events()[0], created_at=iso(START))])
    archive = BoardArchive(client, tmp_path, "viu2", limit=1, split_at=1)
    with pytest.raises(ValueError, match="completude"):
        archive.window(START, START + timedelta(seconds=1))
    assert archive.accepted == []
