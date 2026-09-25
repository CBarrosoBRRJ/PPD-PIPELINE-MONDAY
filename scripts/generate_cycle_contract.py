"""Gera schema/dicionario local; nenhuma conexao GCP."""
import json
from pathlib import Path

from monday_sla_orcamento.cycle_contract import FIELDS, TABLE

root = Path(__file__).resolve().parents[1] / 'tabelas' / TABLE
(root / 'docs').mkdir(parents=True, exist_ok=True)
(root / 'sql').mkdir(parents=True, exist_ok=True)
schema = [{'name': k, 'type': t, 'mode': 'REQUIRED' if required else 'NULLABLE'}
          for k, (t, required) in FIELDS.items()]
(root / 'docs/schema.json').write_text(json.dumps(schema, indent=2), encoding='utf-8')
types = {'INTEGER': 'INT64', 'FLOAT': 'FLOAT64', 'BOOLEAN': 'BOOL'}
columns = ',\n'.join(f"  `{k}` {types.get(t, t)}" + (' NOT NULL' if required else '')
                    for k, (t, required) in FIELDS.items())
(root / 'sql/schema.sql').write_text('-- Candidato: NAO executar antes da migracao transacional.\n'
    f'CREATE TABLE `gglobo-viu-dados-hdg-prd.viu_agenciamento.{TABLE}` (\n{columns}\n) '
    'CLUSTER BY projeto_id, situacao;\n', encoding='utf-8')
