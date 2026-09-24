import json
from copy import deepcopy

import pytest
from monday_comum.board_snapshot import capture, decode

SPEC = {'table': 'monday_backlog_agenciamento_2026', 'board_id': 18429499488,
        'columns': {'status_nome': ('s', 'status'), 'marca': ('t', 'text')}}


class Client:
    def __init__(self):
        self.metadata = {'id': '18429499488', 'items_count': 1,
                         'groups': [{'id': 'g', 'title': 'Grupo'}],
                         'columns': [{'id': 's', 'type': 'status', 'settings_str': '{"labels":{"1":"Entrada"}}'},
                                     {'id': 't', 'type': 'text'}]}
        self.items = [{'id': '123', 'name': 'Projeto', 'group': {'id': 'g'}, 'state': 'active',
                       'column_values': [{'id': 's', 'value': '{"index":1}'},
                                         {'id': 't', 'value': '"Marca"'}]}]

    def board(self):
        return deepcopy(self.metadata)

    def item_pages(self):
        yield self.items


def test_all_items_decoded_no_sla_scope_filter():
    client = Client()
    client.items[0]['name'] = 'PACOTE excluido somente do SLA'
    result = capture(client, SPEC, '2026-09-24T12:00:00Z')
    assert result[0]['status_nome'] == 'Entrada'
    assert result[0]['marca'] == 'Marca'
    assert result[0]['grupo_nome'] == 'Grupo'


@pytest.mark.parametrize('fault', ['missing_column', 'type', 'count', 'duplicate', 'missing_cell', 'empty'])
def test_incomplete_capture_fails(fault):
    client = Client()
    if fault == 'missing_column':
        client.metadata['columns'].pop()
    elif fault == 'type':
        client.metadata['columns'][0]['type'] = 'text'
    elif fault == 'count':
        client.metadata['items_count'] = 2
    elif fault == 'duplicate':
        client.items *= 2
    elif fault == 'missing_cell':
        client.items[0]['column_values'].pop()
    else:
        client.items = []
        client.metadata['items_count'] = 0
    with pytest.raises(ValueError):
        capture(client, SPEC, '2026-09-24T12:00:00Z')


def test_people_cardinality_and_unknown_name_preserved():
    cell = {'value': '{"personsAndTeams":[{"id":1,"kind":"person"},{"id":2,"kind":"team"}]}'}
    result = json.loads(decode(cell, {'type': 'people'}, {}))
    assert len(result) == 2 and all(r['nome'] is None for r in result)


def test_new_dropdown_option_requires_schema():
    with pytest.raises(ValueError):
        decode({'value': '{"ids":[1]}'}, {'type': 'dropdown', 'settings_str': '{"labels":[]}'}, {})


def test_private_archive_only_selected_cells():
    client = Client()
    client.items[0]['column_values'].append({'id': 'out_of_scope', 'value': '"not archived"'})
    archives = {}
    capture(client, SPEC, '2026-09-24T12:00:00Z', archive=lambda k, v: archives.update({k: v}))
    assert len(archives['page-0'][0]['column_values']) == 2
