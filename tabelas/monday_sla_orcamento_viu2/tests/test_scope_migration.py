import base64
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from urllib.error import HTTPError

import pytest
from monday_log_viu2 import publication

SPEC = importlib.util.spec_from_file_location("migrate_scope", Path(__file__).parents[1] / "scripts/migrate_scope.py")
migration = importlib.util.module_from_spec(SPEC)
sys.modules.setdefault("publish_history", publication)
SPEC.loader.exec_module(migration)


def test_fingerprint_normalizes_without_hiding_duplicates():
    schema = [{"name": "interval_id", "type": "STRING"}, {"name": "t", "type": "TIMESTAMP"}]
    a = {"interval_id": "1", "t": "2026-09-01T00:00:00Z"}
    b = {**a, "t": "2026-09-01T00:00:00.000000+00:00"}
    assert migration.fingerprint([a], schema) == migration.fingerprint([b], schema)
    assert migration.fingerprint([a, a], schema) != migration.fingerprint([a], schema)
    with pytest.raises(ValueError):
        migration.fingerprint([{**a, "t": "2026-09-01T00:00:00"}], schema)


def setup(monkeypatch, actual="old"):
    schema = [{"name": "interval_id", "type": "STRING"}]
    old, new = [{"interval_id": "1"}, {"interval_id": "2"}], [{"interval_id": "1"}]
    remote_rows = {"old": old, "new": new, "other": [{"interval_id": "99"}]}[actual]
    monkeypatch.setattr(migration, "payload", lambda root: ({}, schema, old, new))
    class API:
        def request(self, url, method="GET", body=None):
            assert method == "GET", "plan must not write"
            return {"location": "US"}
    monkeypatch.setattr(migration, "GoogleAPI", API)
    monkeypatch.setattr(migration, "identity", lambda api: None)
    monkeypatch.setattr(migration, "remote", lambda *args: (
        {"numRows": str(len(remote_rows)), "lastModifiedTime": "123"},
        migration.fingerprint(remote_rows, schema)))


def test_plan_only_reads(monkeypatch, tmp_path):
    setup(monkeypatch)
    assert migration.run(tmp_path)["status"] == "plan_verified_no_data_writes"


def test_already_applied_verifies_without_rewriting(monkeypatch, tmp_path):
    setup(monkeypatch, "new")
    assert migration.run(tmp_path, apply=True)["status"] == "already_applied_content_verified"


def test_unexpected_remote_content_blocks(monkeypatch, tmp_path):
    setup(monkeypatch, "other")
    with pytest.raises(ValueError, match="difere"):
        migration.run(tmp_path)


@pytest.mark.parametrize("expected", [None, "124"])
def test_stale_or_missing_plan_blocks_apply(monkeypatch, tmp_path, expected):
    setup(monkeypatch)
    with pytest.raises(ValueError, match="desatualizado"):
        migration.run(tmp_path, apply=True, expected_modified=expected)


def test_active_scheduler_blocks(monkeypatch):
    monkeypatch.setattr(migration, "gcloud", lambda *args: json.dumps({"state": "ENABLED"}))
    with pytest.raises(ValueError, match="Pause"):
        migration.writers_stopped()


def test_queued_execution_blocks(monkeypatch):
    monkeypatch.setattr(migration, "gcloud", lambda *args: json.dumps(
        {"state": "PAUSED"} if args[0] == "scheduler" else [{"status": {}}]))
    with pytest.raises(ValueError, match="nao concluida"):
        migration.writers_stopped()


@pytest.mark.parametrize("mode", ["success", "existing", "failed", "lost_ack"])
def test_apply_atomic_load_and_reconciliation(monkeypatch, tmp_path, mode):
    schema = [{"name": "interval_id", "type": "STRING"}]
    old, new = [{"interval_id": "1"}, {"interval_id": "2"}], [{"interval_id": "1"}]
    data = b"treated-fixture"
    calls = []
    state = {"loaded": False, "load": None}
    class API:
        def request(self, url, method="GET", body=None):
            calls.append((url, method))
            if "storage.googleapis.com" in url:
                return {"size": len(data), "md5Hash": base64.b64encode(hashlib.md5(data).digest()).decode()}
            if url == migration.TABLE_URL:
                return {"etag": "stable"}
            if url.endswith("/datasets/" + migration.DATASET):
                return {"location": "US"}
            if method == "POST":
                state["load"] = body["configuration"]["load"]
                assert state["load"]["createDisposition"] == "CREATE_NEVER"
                assert state["load"]["writeDisposition"] == "WRITE_TRUNCATE"
                assert state["load"]["destinationTable"]["tableId"] == migration.TABLE
                if mode == "lost_ack":
                    raise TimeoutError()
                if mode == "existing":
                    raise HTTPError(url, 409, "existing", {}, None)
            state["loaded"] = mode != "failed"
            status = {"state": "DONE"}
            if mode == "failed":
                status["errorResult"] = {"reason": "invalid"}
            return {"configuration": {"load": state["load"]}, "status": status}
    monkeypatch.setattr(migration, "GoogleAPI", API)
    monkeypatch.setattr(migration, "identity", lambda api: None)
    monkeypatch.setattr(migration, "writers_stopped", lambda: None)
    monkeypatch.setattr(migration, "gcloud", lambda *args: None)
    monkeypatch.setattr(migration, "payload", lambda root: ({"filtered.ndjson.gz": data}, schema, old, new))
    monkeypatch.setattr(migration, "remote", lambda *args: (
        {"numRows": 1 if state["loaded"] else 2, "lastModifiedTime": "123", "etag": "stable"},
        migration.fingerprint(new if state["loaded"] else old, schema)))
    if mode in ("failed", "lost_ack"):
        with pytest.raises((RuntimeError, TimeoutError)):
            migration.run(tmp_path, apply=True, expected_modified="123")
    else:
        assert migration.run(tmp_path, apply=True, expected_modified="123")["status"] == "applied_full_content_verified"
    assert sum(method == "POST" for _, method in calls) == 1
