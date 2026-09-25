"""Generate the two project-grain product contracts from executable schemas."""

import json
from pathlib import Path

from monday_sla_orcamento.destination_publication import schema, target
from monday_sla_orcamento.destinations import QUALITY, QUEUE


def main():
    root = Path(__file__).resolve().parents[1]
    types = {'INTEGER': 'INT64', 'FLOAT': 'FLOAT64', 'BOOLEAN': 'BOOL'}
    for name in (QUEUE, QUALITY):
        folder = root / 'tabelas' / name
        (folder / 'docs').mkdir(parents=True, exist_ok=True)
        (folder / 'sql').mkdir(parents=True, exist_ok=True)
        fields = [field.to_api_repr() for field in schema(name)]
        (folder / 'docs/schema.json').write_text(json.dumps(fields, indent=2), encoding='utf-8')
        ddl = ',\n'.join('  `' + f['name'] + '` ' + types.get(f['type'], f['type']) +
                        (' NOT NULL' if f['mode'] == 'REQUIRED' else '') for f in fields)
        (folder / 'sql/schema.sql').write_text(
            '-- Referencia; criacao controlada pelo journal de destinos.\nCREATE TABLE `' +
            target(name) + '` (\n' + ddl + '\n) CLUSTER BY projeto_id;\n', encoding='utf-8')


if __name__ == '__main__':
    main()
