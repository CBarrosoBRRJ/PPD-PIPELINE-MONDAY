"""Daily workers for explicitly scoped board snapshots."""
import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from google.cloud import bigquery
from monday_comum.board_snapshot import capture
from monday_comum.snapshot_publication import BUCKET, PROJECT, SnapshotStore
from sls_orcamento_ppd.clients.monday_client import MondayClient
from sls_orcamento_ppd.config import load_settings
from sls_orcamento_ppd.db.gcs import ObjectStore


class SnapshotClient(MondayClient):
    def board(self):
        data = self.query('''query ($ids: [ID!]!) { boards(ids: $ids) {
          id items_count columns { id title type settings_str } groups { id title }
        } }''', {'ids': [str(self.settings.monday_board_id)]})
        boards = data.get('boards', [])
        if len(boards) != 1:
            raise ValueError('Snapshot: board inexistente ou sem permissao')
        return boards[0]


def main(spec):
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--scheduled-for', required=True)
    parser.add_argument('--result', required=True)
    args = parser.parse_args()
    try:
        if args.env_file != spec['table'] + '-runtime':
            raise ValueError('Snapshot: seletor invalido')
        if datetime.fromisoformat(args.scheduled_for).utcoffset() is None:
            raise ValueError('Snapshot: referencia sem fuso')
        settings = load_settings('.env')
        if settings.bq_project != PROJECT or settings.gcs_bucket != BUCKET or settings.bq_location.upper() != 'US':
            raise ValueError('Snapshot: ambiente fora do escopo')
        objects = ObjectStore(SimpleNamespace(bq_project=PROJECT, gcs_bucket=BUCKET,
                                              gcs_prefix='snapshots/' + spec['table']))
        store = SnapshotStore(bigquery.Client(project=PROJECT), objects, spec)
        with objects.lock():
            store.recover()
            client = SnapshotClient(settings.model_copy(update={'monday_board_id': spec['board_id']}))
            archive_prefix = 'captures/' + uuid.uuid4().hex + '/'
            receipt = store.publish(capture(client, spec, datetime.now(UTC).isoformat(),
                archive=lambda name, value: objects.put_json(archive_prefix + name + '.json', value)))
        with Path(args.result).open('x', encoding='utf-8') as handle:
            json.dump(receipt, handle)
        print(json.dumps({'event': 'snapshot_publication_confirmed', 'product': spec['table'], **receipt}), flush=True)
    except Exception as error:
        print(json.dumps({'severity': 'ERROR', 'event': 'snapshot_worker_failed',
                          'product': spec['table'], 'error_type': type(error).__name__,
                          'schema_issues': getattr(error, 'issues', [])}), flush=True)
        raise SystemExit(1) from None
