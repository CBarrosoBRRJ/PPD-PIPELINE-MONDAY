import json
from pathlib import Path

import pytest
from pipeline_monday import cli, worker_consolidated
from sls_orcamento_ppd import config


@pytest.mark.parametrize(('command', 'options', 'expected'), [
    ('cycles-plan', [], {'cycles_bundle_check': True}),
    ('initialize-cycles', ['--writers-stopped'], {'initialize_cycles': True}),
])
def test_cycles_commands_bind_only_requested_mode(monkeypatch, capsys, command, options, expected):
    manifest = Path(__file__).resolve().parents[1] / 'deploy/pipelines.json'
    monkeypatch.setattr('sys.argv', ['pipeline-monday', command, '--manifest', str(manifest), *options])
    monkeypatch.setattr(config, 'load_settings', lambda _: 'settings')
    calls = []
    def execute(settings, at, **kwargs):
        calls.append((settings, kwargs))
        return {'status': 'test_verified'}
    monkeypatch.setattr(worker_consolidated, 'execute', execute)
    cli.main()
    assert calls == [('settings', expected)]
    assert json.loads(capsys.readouterr().out)['status'] == 'test_verified'


def test_initialize_cycles_requires_writers_stopped(monkeypatch):
    manifest = Path(__file__).resolve().parents[1] / 'deploy/pipelines.json'
    monkeypatch.setattr('sys.argv', ['pipeline-monday', 'initialize-cycles', '--manifest', str(manifest)])
    def forbidden(*a, **kw):
        raise AssertionError('must not call worker')
    monkeypatch.setattr(worker_consolidated, 'execute', forbidden)
    with pytest.raises(SystemExit):
        cli.main()
