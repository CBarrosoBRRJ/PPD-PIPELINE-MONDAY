import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[3] / 'scripts/audit_identity_coverage_cloudshell.py'
spec = importlib.util.spec_from_file_location('identity_coverage_audit', path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def test_distinguishes_missing_identity_from_selected_population():
    mapping = {'rows': [{'globocorp_item_id': '1'}, {'globocorp_item_id': '2'}]}
    rows = [{'item_id': '1', 'entradas_datadas': '0', 'na_consolidada': True},
            {'item_id': '2', 'entradas_datadas': '2', 'na_consolidada': False},
            {'item_id': '3', 'entradas_datadas': '1', 'na_consolidada': 'false'}]
    result = audit.summarize(mapping, rows)
    assert result['itens_por_grupo'] == {'na_consolidada': 1, 'mapeado_fora_consolidada': 1, 'sem_mapa': 1}
    assert result['passagens_entrada_datada']['mapeado_fora_consolidada'] == 2
    assert result['ids_sem_mapa_com_entrada_datada'] == ['3']


def test_inconsistent_membership_blocks():
    with pytest.raises(ValueError, match='divergentes'):
        audit.summarize({'rows': []}, [{'item_id': '1', 'entradas_datadas': '1', 'na_consolidada': True}])
