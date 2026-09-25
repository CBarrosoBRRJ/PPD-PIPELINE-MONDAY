import importlib.util
import json
import sys
from copy import deepcopy
from pathlib import Path

import pytest

scripts = Path(__file__).resolve().parents[3] / 'scripts'
for name in ('audit_project_start_cloudshell', 'audit_destination_split_cloudshell'):
    spec = importlib.util.spec_from_file_location(name, scripts / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
audit = module


def row(order=1, status='Entrada', end=None, current='Entrada'):
    return {'projeto_id': 'p', 'interval_id': str(order), 'ordem_etapa': order,
            'item_id_globocorp': 2, 'status_nome': status, 'status_terminal': False,
            'entrada_status_utc': f'2026-09-24T{9 + order}:00:00Z',
            'saida_status_utc': end, 'ambiente_origem': 'viu2',
            'cadastro_atual_origem_json': json.dumps({
                'board_id': 18429499488, 'item_id': 2, 'status_nome': current,
                'capturado_em': '2026-09-24T20:00:00Z'})}


def test_queue_confirmed_without_source_mutation():
    rows = [row()]
    original = deepcopy(rows)
    output, decisions = audit.partition(rows)
    assert output[audit.QUEUE] == rows
    assert decisions[0]['motivos'] == []
    assert rows == original


def test_stale_entry_is_quality_not_queue():
    output, decisions = audit.partition([row(current='Encerrado')])
    assert len(output[audit.QUALITY]) == 1
    assert 'entrada_isolada_diverge_cadastro_atual' in decisions[0]['motivos']


def test_direct_feedback_is_not_an_error():
    rows = [row(end='2026-09-24T11:00:00Z', current='Aguardando Feedback'),
            row(2, 'Aguardando Feedback', current='Aguardando Feedback')]
    output, _ = audit.partition(rows)
    assert output[audit.SLA] == rows


def test_missing_entry_routes_entire_project_to_quality():
    rows = [row(status='Em revisão', end='2026-09-24T11:00:00Z'),
            row(2, 'Aguardando Feedback')]
    output, _ = audit.partition(rows)
    assert output[audit.QUALITY] == rows
    assert not output[audit.SLA]


def test_correction_reclassifies_next_run():
    assert audit.partition([row(current='Encerrado')])[0][audit.QUALITY]
    assert audit.partition([row()])[0][audit.QUEUE]


def test_null_prefix_preserved_without_synthetic_status():
    rows = [row(status=None, end='2026-09-24T11:00:00Z'), row(2)]
    output, decisions = audit.partition(rows)
    assert output[audit.QUEUE] == rows
    assert decisions[0]['registros_nulos_pre_entrada'] == 1


@pytest.mark.parametrize('fault', ['missing_context', 'duplicate', 'wrong_item'])
def test_technical_failures_block_instead_of_business_exclusion(fault):
    rows = [row()]
    if fault == 'missing_context':
        rows[0]['cadastro_atual_origem_json'] = None
    elif fault == 'wrong_item':
        rows[0]['item_id_globocorp'] = 3
    else:
        rows.append(deepcopy(rows[0]))
    with pytest.raises(ValueError):
        audit.partition(rows)
