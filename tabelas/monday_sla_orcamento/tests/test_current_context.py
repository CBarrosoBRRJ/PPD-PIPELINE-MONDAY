import json

import pytest
from monday_sla_orcamento.current_context import ATTRIBUTES, project


def test_current_context_explicit_not_historical():
    source = {**dict.fromkeys(ATTRIBUTES), 'board_id': 18429499488, 'item_id': 123,
              'capturado_em': '2026-09-24T12:00:00Z', 'versao_contrato': 'board-snapshot-v1',
              'marca': 'Marca atual'}
    row = {'item_id_globocorp': 123, 'cadastro_atual_origem_json': json.dumps(source)}
    result = project(row)
    assert result['cadastro_atual_marca'] == 'Marca atual'
    assert 'marca_nome' not in result
    row['item_id_globocorp'] = 456
    with pytest.raises(ValueError):
        project(row)


def test_absent_context_not_invented():
    assert all(v is None for v in project({}).values())


def test_all_requested_attributes_preserved_without_merging_or_row_expansion():
    attributes = {
        'marca': 'Marca teste',
        'talentos_exclusivos_json': '["Talento A", "Talento B"]',
        'interveniencia': 'Talento C',
        'tipo_projeto': 'Sob demanda',
        'tipo_input': 'Mercado',
        'tipo_output': 'Carta Orçamento',
    }
    for index, field in enumerate((
        'orcamento_json', 'talent_manager_json', 'gp_json',
        'conteudo_json', 'producao_json', 'audiencia_json',
    ), start=1):
        attributes[field] = json.dumps([
            {'id': str(index), 'tipo': 'person', 'nome': 'Pessoa teste'},
            {'id': str(index + 100), 'tipo': 'team', 'nome': None},
        ])
    assert set(attributes) == set(ATTRIBUTES)
    source = {**attributes, 'board_id': 18429499488, 'item_id': 123,
              'capturado_em': '2026-09-24T21:07:08Z', 'versao_contrato': 'board-snapshot-v1'}
    raw = json.dumps(source)
    row = {'item_id_globocorp': 123, 'cadastro_atual_origem_json': raw,
           'talento_nome': 'Nome historico preservado'}
    result = project(row)
    for field, value in attributes.items():
        assert result['cadastro_atual_' + field] == value
    assert result['cadastro_atual_capturado_em'] == source['capturado_em']
    assert result['cadastro_atual_origem_json'] == raw
    assert row['talento_nome'] == 'Nome historico preservado'
    assert 'talento_nome' not in result
