import json
from argparse import Namespace
from pathlib import Path

import pytest
from pipeline_monday import cli

MANIFEST = Path(__file__).resolve().parents[1] / "deploy/pipelines.json"


@pytest.mark.parametrize("stopped,generation", [(False, 1), (True, None), (True, 0), (True, -1)])
def test_apply_requires_guards_before_cloud_access(stopped, generation):
    args = Namespace(command="rename-sla-apply", writers_stopped=stopped,
                     expected_generation=generation)
    with pytest.raises(ValueError):
        cli.maintenance(json.loads(MANIFEST.read_text()), args)


def test_maintenance_failure_hides_exception_values(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["pipeline-monday", "rename-sla-plan", "--manifest", str(MANIFEST)])

    def fail(*args):
        raise RuntimeError("private-value-must-not-leak")

    monkeypatch.setattr(cli, "maintenance", fail)
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    output = capsys.readouterr().out
    assert "private-value" not in output
    assert "sla_destination_migration_failed" in output
