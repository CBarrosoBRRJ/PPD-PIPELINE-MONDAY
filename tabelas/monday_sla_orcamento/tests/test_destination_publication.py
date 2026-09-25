import copy
import json
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import NotFound
from monday_sla_orcamento.destination_publication import (
    CONTRACTS,
    DestinationStore,
    fingerprint,
    schema,
    target,
    transaction,
)
from monday_sla_orcamento.destinations import QUALITY, QUEUE, SLA, build
from test_consolidated_store import Objects
from test_destinations_runtime import candidate


class Client:
    def __init__(self, rows, objects):
        self.objects = objects
        self.rows = {target(SLA): copy.deepcopy(rows)}
        self.jobs = {}
        self.fail = self.timeout = self.lost_ack = False
        self.etag = 'initial'

    def get_table(self, name):
        if name not in self.rows:
            raise NotFound('missing')
        return SimpleNamespace(table_id=name, schema=schema(name.rsplit('.', 1)[1]), etag=self.etag)

    def create_table(self, table, **kwargs):
        self.rows.setdefault(str(table.reference), [])

    def list_rows(self, table):
        return copy.deepcopy(self.rows[table.table_id])

    def get_job(self, job_id, **kwargs):
        if job_id not in self.jobs:
            raise NotFound('missing')
        return self.jobs[job_id]

    def query(self, sql, *, job_config, job_id, location):
        assert location == 'US'
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
                    raw = self.objects.get(path)[0]
                    batch[target(name)] = [json.loads(line) for line in raw.splitlines()]
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
    rows = candidate()
    objects = Objects()
    client = Client(rows, objects)
    descriptor = {'cut': rows[0]['corte_globocorp_utc'], 'rows': len(rows),
                  'fingerprint': fingerprint(SLA, rows)}

    def verify(expected):
        assert fingerprint(SLA, client.rows[target(SLA)]) == expected['fingerprint']
    legacy = SimpleNamespace(control=lambda: ({'active': descriptor, 'pending': None}, 1), verify=verify)
    store = DestinationStore(client, objects)
    store.initialize(legacy)
    outputs, report = build(rows)
    return store, client, legacy, outputs, report, {'cut': descriptor['cut']}


def test_transaction_contains_all_targets_and_no_permanent_ddl(setup):
    store, client, legacy, outputs, report, evidence = setup
    result = store.publish(outputs, report, evidence, legacy)
    assert result['publication_verified']
    assert not client.rows[target(SLA)] and len(client.rows[target(QUEUE)]) == 1
    assert not client.rows[target(QUALITY)]
    assert store.control()[0]['pending'] is None
    sql, _ = transaction(store.control()[0]['active']['tables'], store.objects)
    assert sql.count('BEGIN TRANSACTION') == sql.count('COMMIT TRANSACTION') == 1
    assert sql.count('DELETE FROM') == 3 and sql.count('INSERT INTO') == 3
    assert 'CREATE TABLE ' not in sql


def test_failed_transaction_preserves_all_previous_data(setup):
    store, client, legacy, outputs, report, evidence = setup
    before = copy.deepcopy(client.rows)
    client.fail = True
    with pytest.raises(RuntimeError, match='recusada'):
        store.publish(outputs, report, evidence, legacy)
    assert client.rows == before
    assert store.control()[0]['pending'] is None


def test_timeout_retains_journal_and_recovers_same_job(setup):
    store, client, legacy, outputs, report, evidence = setup
    client.timeout = True
    with pytest.raises(RuntimeError, match='incerto'):
        store.publish(outputs, report, evidence, legacy)
    pending = store.control()[0]['pending']
    assert pending is not None
    client.timeout = False
    store.recover()
    assert len(client.jobs) == 1 and store.control()[0]['active']['job_id'] == pending['job_id']


def test_lost_submission_ack_recovers_without_new_transaction(setup):
    store, client, legacy, outputs, report, evidence = setup
    client.lost_ack = True
    with pytest.raises(ConnectionError):
        store.publish(outputs, report, evidence, legacy)
    store.recover()
    assert len(client.jobs) == 1
    assert store.control()[0]['pending'] is None


def test_modified_candidate_blocks_recovery(setup):
    store, client, legacy, outputs, report, evidence = setup
    client.timeout = True
    with pytest.raises(RuntimeError):
        store.publish(outputs, report, evidence, legacy)
    descriptor = store.control()[0]['pending']['tables'][QUEUE]
    name = descriptor['artifact']
    _, generation = store.objects.get(name)
    store.objects.put(name, b'changed', generation)
    with pytest.raises(ValueError, match='corrompido'):
        store.recover()


def test_unknown_preexisting_new_table_not_adopted():
    objects = Objects()
    client = Client(candidate(), objects)
    client.rows[target(QUEUE)] = []
    legacy = SimpleNamespace(control=lambda: ({'pending': None, 'active': {}}, 1), verify=lambda _: None)
    with pytest.raises(ValueError, match='ja existe'):
        DestinationStore(client, objects).initialize(legacy)
