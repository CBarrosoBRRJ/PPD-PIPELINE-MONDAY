"""Full-board extraction/projection. No writes, no implicit SLA scope filters.

Stable pagination and schema are required; a failed capture never represents deletion.
"""

import json


class SnapshotSchemaError(ValueError):
    def __init__(self, issues):
        super().__init__('Snapshot: schema obrigatorio alterado')
        self.issues = issues


def validate_schema(board, spec):
    if str(board.get('id')) != str(spec['board_id']):
        raise ValueError('Snapshot: board incorreto')
    columns = {c['id']: c for c in board['columns']}
    if len(columns) != len(board['columns']):
        raise ValueError('Snapshot: colunas duplicadas')
    issues = []
    for field, (column_id, kind) in spec['columns'].items():
        if column_id not in columns or columns[column_id]['type'] != kind:
            issues.append({'field': field, 'column_id': column_id, 'expected_type': kind,
                           'reason': 'missing_column' if column_id not in columns else 'changed_type'})
    if issues:
        raise SnapshotSchemaError(issues)
    return columns


def decode(cell, column, people):
    """Keep multi-valued people as JSON, no false historical attribution."""
    value = cell.get('value')
    raw = json.loads(value) if isinstance(value, str) and value else value
    if raw is None:
        return None
    kind = column['type']
    if kind == 'people':
        entries = raw.get('personsAndTeams')
        if not isinstance(entries, list):
            raise ValueError('Snapshot: pessoas malformadas')
        output = []
        for entry in entries:
            identity, entity_kind = str(entry['id']), entry['kind']
            if entity_kind not in {'person', 'team'}:
                raise ValueError('Snapshot: tipo de responsavel desconhecido')
            output.append({'id': identity, 'tipo': entity_kind,
                           'nome': people.get(identity) if entity_kind == 'person' else None})
        return json.dumps(sorted(output, key=lambda v: (v['tipo'], v['id'])), ensure_ascii=False)
    if kind == 'status':
        index = raw.get('index')
        if index is None:
            return None
        labels = json.loads(column.get('settings_str') or '{}').get('labels', {})
        if str(index) not in labels:
            raise ValueError('Snapshot: status sem rotulo no schema')
        return labels[str(index)]
    if kind == 'dropdown':
        ids = raw.get('ids')
        if not isinstance(ids, list):
            raise ValueError('Snapshot: dropdown malformado')
        labels = {str(v['id']): v['name'] for v in
                  json.loads(column.get('settings_str') or '{}').get('labels', [])}
        if any(str(i) not in labels for i in ids):
            raise ValueError('Snapshot: opcao de dropdown desconhecida')
        return json.dumps([labels[str(i)] for i in ids], ensure_ascii=False)
    if kind == 'text':
        if not isinstance(raw, str):
            raise ValueError('Snapshot: texto malformado')
        return raw
    raise ValueError('Snapshot: tipo nao implementado')


def capture(client, spec, captured_at, archive=None):
    before = client.board()
    columns = validate_schema(before, spec)
    selected = {c for c, _ in spec['columns'].values()}
    if archive:
        archive('schema', {**before, 'columns': [c for c in before['columns'] if c['id'] in selected]})
    rows, seen, person_ids = [], set(), set()
    for page_number, page in enumerate(client.item_pages()):
        if archive:
            archive('page-' + str(page_number), [
                {**item, 'column_values': [c for c in item['column_values'] if c['id'] in selected]}
                for item in page])
        for item in page:
            identity = str(item['id'])
            if not identity.isdigit() or int(identity) <= 0 or identity in seen:
                raise ValueError('Snapshot: identidade invalida ou duplicada')
            seen.add(identity)
            cells = {c['id']: c for c in item['column_values']}
            if len(cells) != len(item['column_values']):
                raise ValueError('Snapshot: celulas duplicadas')
            for column_id, kind in spec['columns'].values():
                if column_id not in cells:
                    raise ValueError('Snapshot: celula nao retornada pela origem')
                if kind == 'people':
                    raw = json.loads(cells[column_id].get('value') or 'null')
                    if raw:
                        person_ids.update(str(p['id']) for p in raw.get('personsAndTeams', [])
                                          if p['kind'] == 'person')
            rows.append((item, cells))
    after = client.board()
    validate_schema(after, spec)
    if before != after or len(rows) != int(after['items_count']):
        raise ValueError('Snapshot: schema/contagem mudou ou paginacao incompleta')
    if not rows:
        raise ValueError('Snapshot: board vazio exige revisao antes de substituir publicacao')
    people = {str(p['id']): p['name'] for p in client.users(sorted(person_ids))} if person_ids else {}
    groups = {g['id']: g['title'] for g in before.get('groups', [])}
    output = []
    for item, cells in rows:
        row = {'board_id': int(spec['board_id']), 'item_id': int(item['id']),
               'item_nome': item['name'], 'grupo_id': (item.get('group') or {}).get('id'),
               'grupo_nome': groups.get((item.get('group') or {}).get('id')),
               'estado_item': item.get('state'), 'capturado_em': captured_at,
               'criado_em_origem': item.get('created_at'), 'atualizado_em_origem': item.get('updated_at'),
               'versao_contrato': 'board-snapshot-v1'}
        for name, (column_id, _) in spec['columns'].items():
            row[name] = decode(cells[column_id], columns[column_id], people)
        output.append(row)
    return sorted(output, key=lambda r: r['item_id'])
