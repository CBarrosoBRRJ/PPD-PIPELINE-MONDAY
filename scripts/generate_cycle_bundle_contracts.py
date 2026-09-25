"""Generate physical v18 contracts without modifying legacy executable schemas."""
import json
from pathlib import Path

from monday_sla_orcamento.cycle_destinations import CONTRACTS
from monday_sla_orcamento.cycle_publication import schema

root = Path(__file__).resolve().parents[1]
for table in CONTRACTS:
    folder = root / 'tabelas' / table / 'docs'
    folder.mkdir(parents=True, exist_ok=True)
    fields = [f.to_api_repr() for f in schema(table)]
    (folder / 'schema_ciclos_v18.json').write_text(json.dumps(fields, indent=2), encoding='utf-8')
