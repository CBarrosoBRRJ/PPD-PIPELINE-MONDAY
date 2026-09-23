import json
from copy import deepcopy

import pytest
from historico_viu2.matching import find_candidates, normalized

BOARD = {"columns": [{"id": "folder", "title": "Pasta", "type": "link"},
                     {"id": "brand", "title": "Marca", "type": "text"},
                     {"id": "status", "title": "Status", "type": "status"}]}


def item(key, name="Projeto A", folder="https://example.org/a", brand="Marca"):
    return {"id": str(key), "name": name, "column_values": [
        {"id": "folder", "type": "link", "value": json.dumps({"url": folder})},
        {"id": "brand", "type": "text", "text": brand},
        {"id": "status", "type": "status", "text": "Entrada"}]}


def test_name_and_unique_link_are_candidates_not_approved():
    old, new = [item(1)], [item(2, " PROJETO   A ")]
    original = deepcopy(old)
    result = find_candidates(BOARD, old, BOARD, new)
    row = result["candidates"][0]
    assert row["tier"] == "name_and_unique_link"
    assert row["approved"] is False
    assert "status" not in row["matching_fields"]
    assert result["summary"]["native_ids_in_common"] == 0
    assert old == original


def test_duplicate_name_or_link_not_unique_identity():
    result = find_candidates(BOARD, [item(1), item(2)], BOARD, [item(3), item(4)])
    assert len(result["candidates"]) == 4
    assert all(not r["unique_link_evidence"] for r in result["candidates"])


def test_name_only_empty_fields_dont_match():
    result = find_candidates(BOARD, [item(1, folder="", brand="")], BOARD, [item(2, folder="", brand="")])
    assert result["candidates"][0]["tier"] == "name_or_id_only"
    assert result["candidates"][0]["matching_fields"] == []


def test_renamed_project_same_link_is_review_not_automatic():
    result = find_candidates(BOARD, [item(1)], BOARD, [item(2, name="Outro")])
    assert result["candidates"][0]["tier"] == "link_with_name_or_link_difference"


def test_equal_native_id_still_not_approved():
    result = find_candidates(BOARD, [item(1, name="A", folder="")], BOARD, [item(1, name="B", folder="")])
    assert result["candidates"][0]["same_native_item_id"]
    assert result["summary"]["approved_pairs"] == 0


def test_no_fuzzy_normalization_and_duplicate_source_ids_rejected():
    assert normalized("Ação") != normalized("Acao")
    with pytest.raises(ValueError):
        find_candidates(BOARD, [item(1), item(1)], BOARD, [item(2)])


def test_composite_keys_disambiguate_repeated_name_without_approval():
    old = [item(i, folder=f"https://example.org/{i}", brand=f"Marca {i}") for i in range(1, 7)]
    new = [item(i + 10, folder=f"https://example.org/{i}", brand=f"Marca {i}") for i in range(1, 7)]
    report = find_candidates(BOARD, old, BOARD, new)
    combo = next(r for r in report["combination_statistics"] if r["fields"] == ["name", "brand"])
    assert combo["unique_pairs"] == 6
    assert combo["disambiguated_repeated_names"] == 6
    assert report["summary"]["approved_pairs"] == 0


def test_entry_date_combination_handles_generic_repeated_name():
    board = {"columns": [{"id": "d", "title": "Data de Entrada", "type": "date"}]}
    old, new = [], []
    for i in range(1, 12):
        value = [{"id": "d", "type": "date", "text": f"2026-01-{i:02d}"}]
        old.append({"id": str(i), "name": "Projeto", "column_values": value})
        new.append({"id": str(i + 100), "name": "Projeto", "column_values": value})
    report = find_candidates(board, old, board, new)
    assert len(report["candidates"]) == 11
    assert report["summary"]["unique_name_and_entry_date_pairs"] == 11
    assert report["summary"]["approved_pairs"] == 0
