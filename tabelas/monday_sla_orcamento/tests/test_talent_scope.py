import json
from copy import deepcopy

import pytest
from monday_sla_orcamento.consolidation import build
from monday_sla_orcamento.current_context import ATTRIBUTES
from monday_sla_orcamento.talent_context import exclusion_reasons
from test_consolidation import inputs


def context(names, inter):
    return {**dict.fromkeys(ATTRIBUTES), 'board_id': 18429499488, 'item_id': 2,
            'capturado_em': '2026-09-24T21:00:00Z', 'versao_contrato': 'board-snapshot-v1',
            'talentos_exclusivos_json': json.dumps(names), 'interveniencia': inter}


@pytest.mark.parametrize(('names', 'inter', 'reason'), [
    (['Ana'], 'Bia', 'talento_ambas_colunas'),
    (['Ana'], 'Ana', 'talento_ambas_colunas'),
    ([], None, 'talento_nao_informado'),
    (['  '], ' ', 'talento_nao_informado'),
    (['Squad'], None, 'talento_squad'),
    ([], 'SQUAD DE TALENTOS', 'talento_squad'),
    (['Projeto - Squad comercial'], None, 'talento_squad'),
    (['Ana', 'Bia'], None, 'talento_multiplo'),
])
def test_entire_project_excluded_without_mutating_sources(names, inter, reason):
    old, new, mapping = inputs()
    source = context(names, inter)
    before = deepcopy((old, new, mapping, source))
    rows, report = build(old, new, mapping, current_context=[source])
    assert rows == []
    assert (old, new, mapping, source) == before
    assert report['talent_excluded_selected_projects'] == 1
    assert reason in report['talent_excluded_projects'][mapping['rows'][0]['projeto_id']]
    assert report['excluded_source_rows']['viu2:talento_fora_escopo'] == 1
    assert report['excluded_source_rows']['globocorp:talento_fora_escopo'] == 1


@pytest.mark.parametrize(('names', 'inter', 'flag'), [(['Ana'], None, False), ([], 'Bia', True)])
def test_valid_project_and_corrected_registration_return(names, inter, flag):
    old, new, mapping = inputs()
    assert build(old, new, mapping, current_context=[context([], None)])[0] == []
    rows, report = build(old, new, mapping, current_context=[context(names, inter)])
    assert len(rows) == 2
    assert all(r['eh_interveniencia'] is flag for r in rows)
    assert report['talent_excluded_selected_projects'] == 0


def test_squad_is_word_not_substring():
    assert exclusion_reasons(context(['Esquadrilha'], None)) == []


def test_missing_or_malformed_context_blocks_instead_of_silent_exclusion():
    old, new, mapping = inputs()
    with pytest.raises(ValueError, match='ausente'):
        build(old, new, mapping, current_context=[])
    invalid = context([], None)
    invalid['talentos_exclusivos_json'] = '{invalid'
    with pytest.raises(ValueError):
        build(old, new, mapping, current_context=[invalid])


def test_each_capture_reevaluates_valid_invalid_corrected_without_denylist():
    old, new, mapping = inputs()
    valid = context(['Ana'], None)
    first, _ = build(old, new, mapping, current_context=[valid])
    invalid = context(['Ana'], 'Bia')
    assert build(old, new, mapping, current_context=[invalid])[0] == []
    corrected = context([], 'Bia')
    corrected['capturado_em'] = '2026-09-25T09:00:00Z'
    restored, _ = build(old, new, mapping, current_context=[corrected])
    assert {r['interval_id'] for r in restored} == {r['interval_id'] for r in first}
    assert all(r['talento_nome_atual'] == 'Bia' and r['eh_interveniencia'] for r in restored)
    assert [r['duracao_horas'] for r in restored] == [r['duracao_horas'] for r in first]
