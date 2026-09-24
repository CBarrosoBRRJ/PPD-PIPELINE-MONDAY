"""Generate reference schemas for the two current-board products; no remote writes."""

import json
from pathlib import Path

from monday_backlog_agenciamento_2026 import SPEC as BACKLOG
from monday_comum.snapshot_publication import SnapshotStore
from monday_talentos_exclusivos import SPEC as TALENTS

ROOT = Path(__file__).resolve().parents[1]

for spec in (BACKLOG, TALENTS):
    store = SnapshotStore(None, None, spec)
    directory = ROOT / 'tabelas' / spec['table'] / 'docs'
    directory.mkdir(exist_ok=True)
    (directory / 'schema.json').write_text(
        json.dumps([f.to_api_repr() for f in store.schema], indent=2) + '\n', encoding='utf-8')
