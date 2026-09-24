import json

import pytest
from monday_sla_orcamento.talent_context import project


def row(names=None, inter=None):
    return {'cadastro_atual_origem_json': '{}',
            'cadastro_atual_talentos_exclusivos_json': json.dumps(names) if names is not None else None,
            'cadastro_atual_interveniencia': inter}


@pytest.mark.parametrize(('names', 'inter', 'name', 'flag', 'state'), [
    ([' Ana '], None, 'Ana', False, 'rotulo_unico_na_origem'),
    ([], ' Bia ', 'Bia', True, 'rotulo_unico_na_origem'),
    ([], None, None, None, 'nao_informado'),
    (['  '], ' ', None, None, 'nao_informado'),
    (['Ana', 'Bia'], None, None, None, 'multiplos_exclusivos'),
    (['Ana'], 'Ana', None, None, 'ambas_origens'),
    ([], 'Ana / Bia', None, None, 'interveniencia_requer_revisao'),
])
def test_talent_source(names, inter, name, flag, state):
    source = row(names, inter)
    original = dict(source)
    result = project(source)
    assert source == original
    assert result['talento_nome_atual'] == name
    assert result['eh_interveniencia'] is flag
    assert result['situacao_talento_atual'] == state


def test_both_sources_preserve_each_flag_without_merging_names():
    entries = json.loads(project(row(['Ana'], 'Ana'))['talentos_atuais_json'])
    assert [e['eh_interveniencia'] for e in entries] == [False, True]
    assert entries[1]['texto_nao_estruturado'] is True


def test_no_context():
    result = project({})
    assert result['eh_interveniencia'] is None
    assert result['talentos_atuais_json'] is None
    assert result['situacao_talento_atual'] == 'sem_cadastro'


@pytest.mark.parametrize('names', ['Ana', [1], {}])
def test_invalid_list_blocks(names):
    with pytest.raises(ValueError):
        project(row(names))


def test_v8_schema_stays_unchanged():
    from monday_sla_orcamento.consolidation import PRICING_VERSION, VERSION, fields_for
    assert 'eh_interveniencia' not in fields_for(PRICING_VERSION)
    assert fields_for(VERSION)['eh_interveniencia'] == ('BOOLEAN', False)
