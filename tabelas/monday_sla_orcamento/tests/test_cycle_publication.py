import copy
import json
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import NotFound
from monday_sla_orcamento.cycle_destinations import CONTRACTS, CYCLES, build
from monday_sla_orcamento.cycle_publication import CycleStore, schema, target, validate_bundle
from monday_sla_orcamento.destination_publication import CONTROL as OLD_CONTROL
from monday_sla_orcamento.destination_publication import IDENTITY as OLD_IDENTITY
from monday_sla_orcamento.destination_publication import fingerprint as old_fingerprint
from monday_sla_orcamento.destination_publication import schema as old_schema
from monday_sla_orcamento.destinations import QUALITY, QUEUE, SLA
from monday_sla_orcamento.destinations import build as old_build
from test_consolidated_store import Objects
from test_destinations_runtime import candidate


class Client:
    def __init__(self, rows, objects):
        self.objects = objects
        self.rows = {target(k): copy.deepcopy(v) for k, v in rows.items()}
        self.schemas = {target(k): old_schema(k) for k in rows}
        self.jobs = {}
        self.fail = self.timeout = self.lost_ack = False
        self.etag = 'initial'

    def get_table(self, name):
        if name not in self.rows:
            raise NotFound('missing')
        return SimpleNamespace(table_id=name, schema=self.schemas[name], etag=self.etag)

    def update_table(self, table, fields):
        self.schemas[table.table_id] = table.schema
        for row in self.rows[table.table_id]:
            for field in table.schema:
                row.setdefault(field.name, None)
        return table

    def create_table(self, table, **kwargs):
        name = str(table.reference)
        self.rows.setdefault(name, [])
        self.schemas.setdefault(name, table.schema)

    def list_rows(self, table):
        return copy.deepcopy(self.rows[table.table_id])

    def get_job(self, job_id, **kwargs):
        if job_id not in self.jobs:
            raise NotFound('missing')
        return self.jobs[job_id]

    def query(self, sql, *, job_config, job_id, location):
        assert location == 'US'
        assert sql.count('BEGIN TRANSACTION') == 1 and sql.count('INSERT INTO') == 4
        job = SimpleNamespace(query=sql, state='RUNNING', error_result=None,
                              to_api_repr=lambda: {'configuration': job_config.to_api_repr()})
        def result(timeout):
            if self.timeout:
                raise TimeoutError('uncertain')
            if self.fail:
                job.state, job.error_result = 'DONE', {'reason': 'denied'}
                raise ValueError('failure')
            batch = {}
            for i, name in enumerate(CONTRACTS):
                external = job_config.table_definitions.get('input_' + str(i))
                if external:
                    path = external.source_uris[0].removeprefix('gs://test/consolidado/')
                    batch[target(name)] = [json.loads(line) for line in self.objects.get(path)[0].splitlines()]
                else:
                    batch[target(name)] = []
            self.rows.update(batch)
            self.etag, job.state = job_id, 'DONE'
        job.result = result
        self.jobs[job_id] = job
        if self.lost_ack:
            self.lost_ack = False
            raise ConnectionError('lost acknowledgement')
        return job


@pytest.fixture
def setup():
    rows = candidate('sla')
    old, _ = old_build(rows)
    objects = Objects()
    previous = {'tables': {name: {'rows': len(data), 'fingerprint': old_fingerprint(name, data)}
                           for name, data in old.items()}, 'cut': rows[0]['corte_globocorp_utc']}
    objects.put_json(OLD_CONTROL, {'identity': OLD_IDENTITY, 'active': previous,
                     'initializing': False, 'pending': None}, 0)
    client = Client(old, objects)
    store = CycleStore(client, objects)
    outputs, report = build(rows)
    return store, client, outputs, report, {'cut': previous['cut']}


def test_migration_idempotent_and_four_table_publication(setup):
    store, client, outputs, report, evidence = setup
    store.initialize()
    store.initialize()
    result = store.publish(outputs, report, evidence)
    assert result['publication_verified']
    assert len(client.rows[target(CYCLES)]) == 1
    assert store.control()[0]['pending'] is None
    assert client.schemas[target(SLA)] == schema(SLA)
    store.publish(outputs, report, evidence)
    assert len(client.jobs) == 2
    assert len(client.rows[target(CYCLES)]) == 1


def test_migration_resumes_after_schema_update(setup, monkeypatch):
    store, client, outputs, report, evidence = setup
    original = client.create_table
    def unavailable(*args, **kwargs):
        raise ConnectionError('creation unavailable')
    monkeypatch.setattr(client, 'create_table', unavailable)
    with pytest.raises(ConnectionError):
        store.initialize()
    assert store.control()[0]['initializing'] is True
    with pytest.raises(ValueError, match='inicializacao'):
        store.recover()
    monkeypatch.setattr(client, 'create_table', original)
    store.initialize()
    assert store.publish(outputs, report, evidence)['publication_verified']


def test_queue_is_subset_and_cycle_fk():
    outputs, report = build(candidate())
    checked = validate_bundle(outputs, report)
    assert len(checked[SLA]) == len(checked[QUEUE]) == len(checked[CYCLES]) == 1
    assert checked[SLA][0]['ciclo_id'] == checked[CYCLES][0]['ciclo_id']
    assert checked[CYCLES][0]['operacao_horas_corridas'] is None


@pytest.mark.parametrize('mode', ['fail', 'timeout', 'lost_ack'])
def test_failure_and_recovery(setup, mode):
    store, client, outputs, report, evidence = setup
    store.initialize()
    before = copy.deepcopy(client.rows)
    setattr(client, mode, True)
    with pytest.raises((RuntimeError, ConnectionError)):
        store.publish(outputs, report, evidence)
    assert client.rows == before
    if mode == 'fail':
        assert store.control()[0]['pending'] is None
    else:
        pending = store.control()[0]['pending']
        assert pending
        client.timeout = False
        store.recover()
        assert len(client.jobs) == 1 and store.control()[0]['active']['job_id'] == pending['job_id']


def test_altered_cycle_blocks_before_any_publication(setup):
    store, client, outputs, report, evidence = setup
    outputs[CYCLES][0]['ciclo_id'] = 'wrong'
    with pytest.raises(ValueError, match='relacionamento'):
        store.publish(outputs, report, evidence)
    assert not client.jobs


def test_pending_corruption_stops_recovery(setup):
    store, client, outputs, report, evidence = setup
    store.initialize()
    client.timeout = True
    with pytest.raises(RuntimeError):
        store.publish(outputs, report, evidence)
    path = store.control()[0]['pending']['tables'][CYCLES]['artifact']
    _, generation = store.objects.get(path)
    store.objects.put(path, b'changed', generation)
    with pytest.raises(ValueError, match='corrompido'):
        store.recover()


def test_preexisting_table_refused_and_legacy_control_protected(setup):
    store, client, outputs, report, evidence = setup
    client.rows[target(CYCLES)] = []
    client.schemas[target(CYCLES)] = schema(CYCLES)
    with pytest.raises(ValueError, match='preexistente'):
        store.initialize()
    del client.rows[target(CYCLES)]
    store.initialize()
    old, generation = store.objects.get(OLD_CONTROL)
    store.objects.put(OLD_CONTROL, old, generation)
    with pytest.raises(ValueError, match='legado'):
        store.publish(outputs, report, evidence)


def test_same_project_can_have_quality_without_losing_sla():
    outputs, report = build(candidate())
    assert {r['projeto_id'] for r in outputs[QUALITY]} <= {r['projeto_id'] for r in outputs[SLA]}
    assert report['source_projects'] == report['accepted_projects'] == 1
