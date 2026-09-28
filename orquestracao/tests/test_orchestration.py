import copy
import json
import subprocess
from pathlib import Path

import pytest
from pipeline_monday.runner import execute_product, plan, run


def product(name, dependencies=()):
    return {"id": name, "runner": "sla_orcamento", "env_file": f".env.{name}", "depends_on": list(dependencies)}


def manifest(*products):
    return {"version": 1, "deadline_seconds": 100, "products": list(products)}


def test_order_and_input_preserved():
    document = manifest(product("joined", ["source"]), product("source"))
    original = copy.deepcopy(document)
    assert [p["id"] for p in plan(document)] == ["source", "joined"]
    assert document == original


@pytest.mark.parametrize("document", [
    manifest(), manifest(product("x"), product("x")),
    manifest(product("x", ["missing"])),
    manifest(product("x", ["y"]), product("y", ["x"])),
    manifest({**product("x"), "runner": "historico_viu2"}),
    manifest({**product("x"), "token": "must-not-be-accepted"}),
    manifest(product("x"), {**product("y"), "env_file": ".env.x"}),
    {**manifest(product("x")), "deadline_seconds": 3601},
])
def test_invalid_plan_fails_before_execution(document):
    with pytest.raises(ValueError):
        run(document, execute=lambda *_: pytest.fail("must not execute"))


@pytest.mark.parametrize("source_status", ["failed", "skipped"])
def test_failed_or_skipped_source_blocks_dependent_but_not_independent(source_status):
    called = []
    def execute(p, *_):
        called.append(p["id"])
        return {"status": source_status if p["id"] == "source" else "success"}
    result = run(manifest(product("source"), product("joined", ["source"]), product("independent")), execute=execute)
    assert called == ["source", "independent"]
    assert result["products"]["joined"]["status"] == "blocked"
    assert result["status"] == "failed"


def test_same_scheduled_time_and_global_deadline():
    times = iter([0, 1, 101])
    called = []
    result = run(manifest(product("first"), product("second")), clock=lambda: next(times),
                 execute=lambda p, at, timeout: called.append((at, timeout)) or {"status": "success"},
                 scheduled_for="2026-09-21T09:00:00+00:00")
    assert called == [("2026-09-21T09:00:00+00:00", 99)]
    assert result["products"]["second"]["reason"] == "global_deadline"


def test_skipped_is_not_successful_refresh():
    result = run(manifest(product("x")), execute=lambda *_: {"status": "skipped"})
    assert result["status"] == "skipped"


def test_verified_reused_source_can_feed_consolidation():
    called = []
    def execute(p, *_):
        called.append(p["id"])
        return {"status": "skipped", "publication_verified": True}
    result = run(manifest(product("source"), product("joined", ["source"])), execute=execute)
    assert called == ["source", "joined"]
    assert result["status"] == "success"


class FakeProcess:
    def __init__(self, command, returncode=0, receipt=None, waits=()):
        self.command, self.returncode, self.signals = command, returncode, []
        self.waits = list(waits)
        if receipt is not None:
            Path(command[-1]).write_text(json.dumps(receipt))

    def wait(self, timeout=None):
        if self.waits and self.waits.pop(0) == "timeout":
            raise subprocess.TimeoutExpired("worker", timeout)
        return self.returncode

    def terminate(self):
        self.signals.append("terminate")

    def kill(self):
        self.signals.append("kill")


def fake_popen(monkeypatch, **options):
    processes = []

    def popen(command, **kwargs):
        assert kwargs["shell"] is False
        processes.append(FakeProcess(command, **options))
        return processes[-1]
    monkeypatch.setattr(subprocess, "Popen", popen)
    return processes


def test_worker_requires_verified_receipt(monkeypatch):
    fake_popen(monkeypatch, receipt={"status": "success", "publication_verified": False})
    assert execute_product(product("x"), "2026-09-21T09:00:00Z", 12)["status"] == "failed"


def test_successful_worker_receipt(monkeypatch):
    fake_popen(monkeypatch, receipt={"status": "success", "publication_verified": True, "gold_rows": 5, "secret": "not-forwarded"})
    result = execute_product(product("x"), "2026-09-21T09:00:00Z", 12)
    assert result == {"status": "success", "publication_verified": True, "gold_rows": 5}


def test_timeout_terminates_gracefully_before_kill(monkeypatch):
    graceful = fake_popen(monkeypatch, waits=["timeout"])
    assert execute_product(product("x"), "2026-09-21T09:00:00Z", 1)["reason"] == "timeout_inspect_product_lock"
    assert graceful[0].signals == ["terminate"]
    stuck = fake_popen(monkeypatch, waits=["timeout", "timeout"])
    assert execute_product(product("x"), "2026-09-21T09:00:00Z", 1)["reason"] == "timeout_inspect_product_lock"
    assert stuck[0].signals == ["terminate", "kill"]


def test_product_not_started_without_minimum_time():
    times = iter([0, 1, 90])
    called = []
    result = run(manifest(product("first"), product("second")), clock=lambda: next(times),
                 execute=lambda p, at, timeout: called.append(p["id"]) or {"status": "success"})
    assert called == ["first"]
    assert result["products"]["second"] == {"status": "blocked", "reason": "insufficient_time_for_product"}
    assert result["status"] == "failed"
