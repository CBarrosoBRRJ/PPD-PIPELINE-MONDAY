"""Read-only real-board rehearsal, no BQ/GCS/email writes."""

from datetime import UTC, datetime

from monday_backlog_agenciamento_2026 import SPEC as BACKLOG
from monday_comum.board_snapshot import capture
from monday_comum.snapshot_publication import SnapshotStore
from monday_talentos_exclusivos import SPEC as TALENTS
from sls_orcamento_ppd.config import load_settings

from pipeline_monday.worker_snapshot import SnapshotClient


def run():
    settings = load_settings('.env')
    results = {}
    for spec in (BACKLOG, TALENTS):
        client = SnapshotClient(settings.model_copy(update={'monday_board_id': spec['board_id']}))
        try:
            rows = capture(client, spec, datetime.now(UTC).isoformat())
            store = SnapshotStore(None, None, spec)
            store.canonical(rows)
            results[spec['table']] = {'status': 'validated', 'rows': len(rows), 'columns': len(store.fields)}
        except Exception as error:
            results[spec['table']] = {'status': 'failed', 'error_type': type(error).__name__,
                                     'schema_issues': getattr(error, 'issues', [])}
    return {'event': 'snapshot_preflight', 'status': 'success' if all(
        r['status'] == 'validated' for r in results.values()) else 'failed',
        'cloud_modified': False, 'products': results}
