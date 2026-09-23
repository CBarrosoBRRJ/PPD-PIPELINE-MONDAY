import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "label_plan", Path(__file__).parents[1] / "scripts/plan_label_migration.py")
plan = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(plan)


@pytest.mark.parametrize("case", ["ok", "changed", "pending", "wrong_content"])
def test_preflight_only_reads_and_rejects_unstable_state(monkeypatch, tmp_path, case):
    schema = [{"name": "interval_id", "type": "STRING"}]
    old = [{"interval_id": "one"}]
    monkeypatch.setattr(plan, "load_package", lambda root: (schema, old, old))
    reads = []

    def command(*args):
        reads.append(args)
        if args[:2] == ("bq", "show"):
            calls = sum(a[:2] == ("bq", "show") for a in reads)
            return {"etag": str(calls) if case == "changed" else "stable",
                    "schema": {"fields": schema}, "numRows": "1", "lastModifiedTime": "123"}
        if args[0] == "bq" and "query" in args:
            assert args[-1].startswith("SELECT ")
            return [{"registro": json.dumps({"interval_id": "other" if case == "wrong_content" else "one"})}]
        assert args[:3] == ("gcloud", "storage", "cat")
        return {"pending": {} if case == "pending" else None, "identity": {}, "active": {}}

    monkeypatch.setattr(plan, "command", command)
    if case == "ok":
        result = plan.run(tmp_path)
        assert result["status"] == "read_only_plan_verified"
        assert not result["cloud_modified"] and not result["apply_available"]
    else:
        with pytest.raises(ValueError):
            plan.run(tmp_path)
