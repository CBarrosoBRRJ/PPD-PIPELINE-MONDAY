from datetime import UTC, datetime

import pytest

from sls_orcamento_ppd.models.project_mapping import approved_project_index

PROJECT = "f7cc870c-1996-4100-9fb5-73fba2a1ecb2"


def row(**changes):
    return {
        "projeto_id": PROJECT, "environment": "viu2", "account_id": "5890468",
        "board_id": 18393336134, "item_id": 1, "review_status": "approved",
        "evidence_ref": "test-migration-record", "reviewed_by": "test-reviewer",
        "reviewed_at": datetime(2026, 9, 21, tzinfo=UTC), **changes,
    }


def test_two_native_ids_one_project():
    result = approved_project_index([
        row(), row(environment="globocorp", account_id="21453629", board_id=18429499488, item_id=2),
    ])
    assert len(result) == 2
    assert set(result.values()) == {PROJECT}


@pytest.mark.parametrize("status", ["pending", "ambiguous"])
def test_unreviewed_match_never_joins(status):
    assert approved_project_index([row(review_status=status, projeto_id=None)]) == {}


@pytest.mark.parametrize("change", [
    {"evidence_ref": ""}, {"reviewed_by": ""}, {"projeto_id": "project-name"},
    {"account_id": "wrong"}, {"reviewed_at": datetime(2026, 9, 21)}, {"item_id": True},
])
def test_invalid_map_blocks_join(change):
    with pytest.raises(ValueError):
        approved_project_index([row(**change)])


def test_duplicate_native_key_rejected():
    with pytest.raises(ValueError, match="repetida"):
        approved_project_index([row(), row()])


def test_silent_merger_of_projects_rejected():
    with pytest.raises(ValueError, match="fusão"):
        approved_project_index([row(), row(item_id=2)])
