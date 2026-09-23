from copy import deepcopy

import pytest
from monday_comum.escopo_sla import (
    coluna_input,
    filtrar_projetos,
    ler_input,
    motivos_exclusao,
    motivos_input,
)


@pytest.mark.parametrize("value", ["ViU First", " viu FIRST ", "Proativo", "PROATIVO"])
def test_input_deny_list(value):
    assert motivos_input(value)


@pytest.mark.parametrize("value", [None, "", "  ", "Mercado", "Inbound", "ViU", "Interna", "Globo", "OTR", "Outro"])
def test_input_empty_and_other_values_are_allowed(value):
    assert not motivos_input(value)


def test_missing_column_is_not_an_empty_input():
    with pytest.raises(ValueError):
        coluna_input({"columns": []})
    with pytest.raises(ValueError):
        ler_input({"id": "x", "type": "status"}, {"column_values": []})


def test_input_status_label_fallback_and_blank():
    column = {"id": "x", "type": "status", "settings_str": '{"labels":{"1":"Proativo"}}'}
    assert ler_input(column, {"column_values": [{"id": "x", "text": "", "value": '{"index":1}'}]}) == "Proativo"
    assert ler_input(column, {"column_values": [{"id": "x", "text": "", "value": None}]}) is None


def test_unverified_project_removed_but_confirmed_blank_kept():
    rows = [{"board_id": 1, "item_id": item, "projeto_nome": "Campanha"}
            for item in (1, 2, 2, 3)]
    original = deepcopy(rows)
    assert filtrar_projetos(rows, {(1, 1): None, (1, 3): "Mercado"}) == [rows[0], rows[3]]
    assert filtrar_projetos(rows, {}) == []
    assert rows == original


@pytest.mark.parametrize("title", [
    "[Upfront 2027] Novela III", "[Globoplay - Originals | Upfront]",
    "[Sem marca] Samira", "[Montadora - Marca em sigilo] Pedro Bial",
    "[Marca não revelada | Varejo] Milena", "Marca a definir - Projeto",
    "[Club Social] Curadoria de Talentos - Diana", "[Mídia Kit] Karine Alves",
    "[Mídiakit] Teste", "[Levop] Card temáticos copa do mundo",
    "[Análise das Redes] Ticiane Pinheiro", "[Pacote] Eliana em Família",
    "Pacote Creators Squad", "  [  pácote ] Teste", "SEM   MARCA Teste",
])
def test_user_exclusions(title):
    assert motivos_exclusao(title)


@pytest.mark.parametrize("title", [
    "[Seara] Bia Reis_ Pacote Rock in Rio", "[Unilever] Pacote Efeméride",
    "[Tic Tac] Pacote", "[Perdigão] Pacote", "[Banco Mercantil] Pacote",
    "Pacotex campanha", None, "", "Campanha comercial",
])
def test_keep_commercial_titles(title):
    assert not motivos_exclusao(title)


def test_brand_column_does_not_exclude_and_whole_project_removed():
    rows = [
        {"board_id": 1, "item_id": 1, "projeto_nome": "Campanha", "marca_original": "Sem Marca"},
        {"board_id": 1, "item_id": 2, "projeto_nome": "[Levop] Interno"},
        {"board_id": 1, "item_id": 2, "projeto_nome": "Outro nome"},
        {"board_id": 2, "item_id": 2, "projeto_nome": "Campanha"},
    ]
    original = deepcopy(rows)
    assert filtrar_projetos(rows) == [rows[0], rows[3]]
    assert rows == original
