import importlib.util
import json
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parents[1] / 'scripts'


@pytest.fixture(params=['pricing', 'talent'])
def migration(monkeypatch, request):
    monkeypatch.syspath_prepend(str(SCRIPTS))
    spec = importlib.util.spec_from_file_location('pricing_migration', SCRIPTS / 'migrate_pricing_contract.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if request.param == 'talent':
        talent_spec = importlib.util.spec_from_file_location('talent_migration', SCRIPTS / 'migrate_talent_contract.py')
        talent = importlib.util.module_from_spec(talent_spec)
        talent_spec.loader.exec_module(talent)
        module = talent.engine()
        assert module.OLD['contract'] == 'sla-consolidado-precificacao-v8'
        assert module.NEW['contract'] == 'sla-consolidado-talentos-v9'
    return module


def test_plan_no_write(migration, monkeypatch):
    value = {'identity': migration.OLD, 'active': {'rows': 10, 'fingerprint': 'a'*64}}
    monkeypatch.setattr(migration, 'read', lambda: (value, '123'))
    assert migration.run()['rows'] == 10


def test_stale_fingerprint_blocks(migration, monkeypatch):
    value = {'identity': migration.OLD, 'active': {'rows': 10, 'fingerprint': 'a'*64}}
    monkeypatch.setattr(migration, 'read', lambda: (value, '123'))
    monkeypatch.setattr(migration.base, 'stopped', lambda _: None)
    with pytest.raises(ValueError, match='desatualizado'):
        migration.run(apply=True, generation='123', fingerprint='b'*64, image='image@sha256:'+'c'*64)


def test_cas_preserves_previous_active(migration, monkeypatch):
    value = {'identity': migration.OLD, 'pending': None,
             'active': {'rows': 10, 'fingerprint': 'a'*64, 'artifact': 'original'}}
    updated = {**value, 'identity': migration.NEW}
    replies = iter([(value, '123'), (value, '123'), (updated, '124')])
    monkeypatch.setattr(migration, 'read', lambda: next(replies))
    monkeypatch.setattr(migration.base, 'stopped', lambda _: None)
    def write(*args):
        assert '--if-generation-match=123' in args
        assert json.loads(Path(args[-2]).read_text()) == updated
    monkeypatch.setattr(migration.base, 'cli', write)
    assert migration.run(apply=True, generation='123', fingerprint='a'*64,
                         image='image@sha256:'+'c'*64)['tables_modified'] is False


def test_pending_blocks(migration, monkeypatch):
    values = iter([{'generation': '123'}, {'identity': migration.OLD, 'pending': {}}, {'generation': '123'}])
    monkeypatch.setattr(migration.base, 'cli', lambda *args: json.dumps(next(values)))
    with pytest.raises(ValueError, match='pendente'):
        migration.read()
