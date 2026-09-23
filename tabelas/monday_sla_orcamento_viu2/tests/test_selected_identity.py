from copy import deepcopy

import pytest
from historico_viu2.selected_identity import select_identity


def candidate(old="1", new="2", **updates):
    return {"viu2_item_id": old, "globocorp_item_id": new, "same_name": True,
            "unique_name_and_entry_date": True, "conflicting_link_fields": [],
            "matching_fields": ["data", "brand"], "different_fields": [],
            "unique_link_evidence": [], **updates}


def test_stable_identity_and_no_implicit_approval():
    report = {"candidates": [candidate()]}
    before = deepcopy(report)
    result = select_identity(report, ["1"], ["2", "3"])
    assert report == before
    row = result["rows"][0]
    assert not row["sla_approved"] and not row["individual_human_review"]
    assert result["unlinked_globocorp"] == ["3"]
    assert select_identity(report, ["1"], ["2"])["rows"][0]["projeto_id"] == row["projeto_id"]


def test_conflict_and_missing_match_preserved_as_exclusions():
    result = select_identity({"candidates": [candidate(conflicting_link_fields=["folder"])]}, ["1", "3"], ["2"])
    assert not result["rows"]
    assert result["summary"]["exclusion_reasons"] == {"conflicting_links": 1, "no_unique_name_and_entry_date": 1}
    assert all(r["raw_preserved"] for r in result["excluded_viu2"])


@pytest.mark.parametrize("rows", [
    [candidate(), candidate(new="3")], [candidate(), candidate(old="3")],
    [candidate(), candidate()], [candidate(old="999")],
    [candidate(matching_fields=["data"])], [candidate(same_name=False)],
])
def test_invalid_mapping_rejected(rows):
    with pytest.raises(ValueError):
        select_identity({"candidates": rows}, ["1", "3"], ["2", "3"])
