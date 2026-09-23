import importlib.util
import json
import sys
from pathlib import Path

import pytest
from monday_log_viu2 import publication

DIRECTORY = Path(__file__).parents[1] / "scripts"
sys.modules.setdefault("publish_history", publication)


def load(name):
    spec = importlib.util.spec_from_file_location(name, DIRECTORY / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sys.modules.setdefault("migrate_scope", load("migrate_scope"))
sys.modules.setdefault("plan_label_migration", load("plan_label_migration"))
migration = load("migrate_labels")


@pytest.mark.parametrize("case", ["success", "stale", "changed", "pending_resume"])
def test_coordinated_apply_preserves_active_and_checks_generation(monkeypatch, tmp_path, case):
    original = {"identity": migration.OLD_IDENTITY, "active": {"fingerprint": "original"}, "pending": None}
    state = {"control": original, "generation": "10", "writes": 0}
    monkeypatch.setattr(migration, "payload", lambda root: None)
    monkeypatch.setattr(migration, "control", lambda: (state["control"], state["generation"]))
    monkeypatch.setattr(migration, "stopped", lambda image: None)
    monkeypatch.setattr(migration, "GoogleAPI", lambda: object())
    monkeypatch.setattr(migration, "identity", lambda api: None)
    monkeypatch.setattr(migration, "upload_source", lambda *args: None)

    def run(*args, **kwargs):
        if case == "changed":
            state["generation"] = "11"
        return {"status": "already_applied_content_verified" if case == "pending_resume" else "applied_full_content_verified"}

    monkeypatch.setattr(migration.loader, "run", run)

    def gcloud(*args):
        assert args[:3] == ("storage", "cp", "--if-generation-match=10")
        updated = json.loads(Path(args[-2]).read_text())
        assert updated["active"] == original["active"]
        state.update(control=updated, generation="12", writes=state["writes"] + 1)

    monkeypatch.setattr(migration, "gcloud", gcloud)
    if case in {"stale", "changed"}:
        with pytest.raises(ValueError):
            migration.run(tmp_path, apply=True, expected_generation="9" if case == "stale" else "10")
        assert state["writes"] == 0
    else:
        result = migration.run(tmp_path, apply=True, expected_generation="10")
        assert result["daily_rebuild_required"]
        assert state["control"]["identity"] == migration.NEW_IDENTITY
        assert state["writes"] == 1


def test_plan_has_no_writes(monkeypatch, tmp_path):
    monkeypatch.setattr(migration, "payload", lambda root: None)
    monkeypatch.setattr(migration, "control", lambda: ({"identity": migration.OLD_IDENTITY}, "10"))
    monkeypatch.setattr(migration.loader, "run", lambda *a, **k: {"status": "plan"})
    monkeypatch.setattr(migration, "GoogleAPI", lambda: pytest.fail("must not write"))
    assert migration.run(tmp_path)["control_generation"] == "10"


def test_active_schedule_blocks(monkeypatch):
    monkeypatch.setattr(migration, "gcloud", lambda *a: json.dumps({"state": "ENABLED"}))
    with pytest.raises(ValueError, match="pausada"):
        migration.stopped("image@sha256:123")


@pytest.mark.parametrize("case", ["daily", "wrong_image", "running", "ok"])
def test_writer_guard_checks_job_and_executions(monkeypatch, case):
    def gcloud(*args):
        if args[0] == "scheduler":
            return json.dumps({"state": "PAUSED"})
        if args[2] == "describe":
            container = {"image": "wrong" if case == "wrong_image" else "image@sha256:123",
                         "command": ["pipeline-monday"],
                         "args": ["daily" if case == "daily" else "plan", "--manifest", "/app/pipelines.json"]}
            return json.dumps({"spec": {"template": {"spec": {"template": {"spec": {"containers": [container]}}}}}})
        return json.dumps([{"status": {}}] if case == "running" else [])
    monkeypatch.setattr(migration, "gcloud", gcloud)
    if case == "ok":
        migration.stopped("image@sha256:123")
    else:
        with pytest.raises(ValueError):
            migration.stopped("image@sha256:123")


def test_resume_after_control_commit_does_not_rewrite_control(monkeypatch, tmp_path):
    monkeypatch.setattr(migration, "payload", lambda root: None)
    monkeypatch.setattr(migration, "control", lambda: ({"identity": migration.NEW_IDENTITY}, "12"))
    monkeypatch.setattr(migration, "stopped", lambda image: None)
    monkeypatch.setattr(migration, "GoogleAPI", lambda: object())
    monkeypatch.setattr(migration, "identity", lambda api: None)
    monkeypatch.setattr(migration, "upload_source", lambda *args: None)
    monkeypatch.setattr(migration.loader, "run", lambda *a, **k: {"status": "already_applied_content_verified"})
    monkeypatch.setattr(migration, "gcloud", lambda *args: pytest.fail("control must not be rewritten"))
    assert migration.run(tmp_path, apply=True)["control_status"] == "already_migrated"
