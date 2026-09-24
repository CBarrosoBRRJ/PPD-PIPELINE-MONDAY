import json
from copy import deepcopy
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import NotFound
from monday_comum.snapshot_publication import SnapshotStore
from test_board_snapshot import SPEC, Client, capture


class Objects:
    def __init__(self):
        self.data = {}

    def get(self, name):
        return self.data.get(name, (None, 0))

    def put(self, name, content, generation=0, **kwargs):
        assert self.get(name)[1] == generation
        self.data[name] = (content, generation + 1)
        return generation + 1

    def put_json(self, name, value, generation=0):
        return self.put(name, json.dumps(value).encode(), generation)

    def uri(self, name):
        return 'gs://test/' + name


class BigQuery:
    def __init__(self, objects):
        self.objects, self.jobs, self.table, self.rows = objects, {}, None, []
        self.loads, self.lose_ack = 0, False

    def get_table(self, target):
        if self.table is None:
            raise NotFound('missing')
        return self.table

    def list_rows(self, table):
        return deepcopy(self.rows)

    def get_job(self, identity, **kwargs):
        if identity not in self.jobs:
            raise NotFound('missing')
        return self.jobs[identity]

    def load_table_from_uri(self, uri, target, job_id, job_config, **kwargs):
        self.loads += 1
        rows = [json.loads(line) for line in self.objects.get(uri.removeprefix('gs://test/'))[0].splitlines()]
        def finish(timeout):
            self.rows = rows
            self.table = SimpleNamespace(schema=job_config.schema, etag=str(self.loads))
            if self.lose_ack:
                self.lose_ack = False
                raise TimeoutError()
        job = SimpleNamespace(destination=target, source_uris=[uri],
                              write_disposition=job_config.write_disposition,
                              schema=job_config.schema, state='DONE', error_result=None, result=finish)
        self.jobs[job_id] = job
        return job


def setup():
    objects = Objects()
    client = BigQuery(objects)
    store = SnapshotStore(client, objects, SPEC)
    rows = capture(Client(), SPEC, '2026-09-24T12:00:00Z')
    return store, client, objects, rows


def test_create_then_replace_edits_inclusions_and_removals():
    store, client, _, rows = setup()
    assert store.publish(rows)['publication_verified']
    new = {**rows[0], 'item_id': 456, 'marca': 'Outra', 'capturado_em': '2026-09-25T12:00:00Z'}
    store.publish([new])
    assert len(client.rows) == 1 and client.rows[0]['item_id'] == 456
    assert client.loads == 2


def test_uncertain_result_recovers_same_job():
    store, client, _, rows = setup()
    client.lose_ack = True
    with pytest.raises(RuntimeError, match='incerto'):
        store.publish(rows)
    assert store.control()[0]['pending']
    store.recover()
    assert client.loads == 1 and store.control()[0]['pending'] is None


def test_corruption_blocks_recovery():
    store, client, objects, rows = setup()
    client.lose_ack = True
    with pytest.raises(RuntimeError):
        store.publish(rows)
    descriptor = store.control()[0]['pending']
    artifact = descriptor['artifact']
    objects.put(artifact, b'corrupt', objects.get(artifact)[1])
    with pytest.raises(ValueError, match='corrompido'):
        store.recover()


def test_empty_and_external_edits_do_not_overwrite():
    store, client, _, rows = setup()
    store.publish(rows)
    with pytest.raises(ValueError, match='vazia'):
        store.publish([])
    client.rows[0]['marca'] = 'external'
    with pytest.raises(ValueError, match='divergente'):
        store.publish(rows)
    assert client.loads == 1


def test_existing_table_not_adopted():
    store, client, _, _ = setup()
    client.table = object()
    with pytest.raises(ValueError, match='sem controle'):
        store.control()
