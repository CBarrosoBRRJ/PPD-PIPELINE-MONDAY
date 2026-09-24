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
