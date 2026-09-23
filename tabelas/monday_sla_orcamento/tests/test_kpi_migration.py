import copy
import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "migrate_kpi_contract", Path(__file__).parents[1] / "scripts" / "migrate_kpi_contract.py")
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


def control():
    return {"identity": migration.OLD, "pending": None,
            "active": {"fingerprint": migration.FINGERPRINT, "rows": 9648, "artifact": "unchanged"}}


def test_plan_has_no_writes(monkeypatch):
    monkeypatch.setattr(migration, "read_control", lambda: (control(), "123"))
    monkeypatch.setattr(migration, "cli", lambda *a: pytest.fail("unexpected write"))
    assert migration.run()["status"] == "plan_no_writes"


def test_stale_generation_blocks(monkeypatch):
    monkeypatch.setattr(migration, "read_control", lambda: (control(), "124"))
    monkeypatch.setattr(migration, "stopped", lambda _: None)
    with pytest.raises(ValueError, match="Geracao"):
        migration.run(apply=True, expected_generation="123", image="test")


def test_cas_preserves_active(monkeypatch):
    original = control()
    updated = {**original, "identity": migration.NEW}
    replies = iter([(original, "123"), (copy.deepcopy(original), "123"), (updated, "124")])
    monkeypatch.setattr(migration, "read_control", lambda: next(replies))
    monkeypatch.setattr(migration, "stopped", lambda _: None)
    def write(*args):
        assert "--if-generation-match=123" in args
        assert json.loads(Path(args[-2]).read_text()) == updated
    monkeypatch.setattr(migration, "cli", write)
    assert migration.run(apply=True, expected_generation="123", image="test")["status"] == "contract_migrated"


def test_concurrent_control_change_blocks(monkeypatch):
    replies = iter([(control(), "123"), (control(), "124")])
    monkeypatch.setattr(migration, "read_control", lambda: next(replies))
    monkeypatch.setattr(migration, "stopped", lambda _: None)
    with pytest.raises(ValueError, match="Controle mudou"):
        migration.run(apply=True, expected_generation="123", image="test")


def test_active_agenda_blocks(monkeypatch):
    monkeypatch.setattr(migration, "cli", lambda *a: '{"state":"ENABLED"}')
    with pytest.raises(ValueError, match="Pause"):
        migration.stopped("us-central1-docker.pkg.dev/" + migration.PROJECT + "/viu-pipelines/pipeline-monday@sha256:test")


def test_new_identity_idempotent(monkeypatch):
    current = {**control(), "identity": migration.NEW}
    monkeypatch.setattr(migration, "read_control", lambda: (current, "125"))
    monkeypatch.setattr(migration, "stopped", lambda _: None)
    assert migration.run(apply=True, expected_generation="123", image="test")["status"] == "already_migrated"


@pytest.mark.parametrize("fault", ["pending", "fingerprint", "rows", "identity", "generation"])
def test_plan_rejects_wrong_or_unstable_control(monkeypatch, fault):
    value = copy.deepcopy(control())
    if fault == "pending":
        value["pending"] = {"job": "unfinished"}
    elif fault == "fingerprint":
        value["active"]["fingerprint"] = "other"
    elif fault == "rows":
        value["active"]["rows"] = 1
    elif fault == "identity":
        value["identity"]["map_sha"] = "other"
    replies = iter([json.dumps({"generation": "123"}), json.dumps(value),
                    json.dumps({"generation": "124" if fault == "generation" else "123"})])
    monkeypatch.setattr(migration, "cli", lambda *a: next(replies))
    with pytest.raises(ValueError):
        migration.read_control()
