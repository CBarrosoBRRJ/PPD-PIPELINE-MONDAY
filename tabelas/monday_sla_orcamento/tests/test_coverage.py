import pytest
from monday_sla_orcamento.coverage import audit


def test_missing_identity_is_reported_not_approved():
    source = [{"item_id": 2, "status_nome": "Entrada", "entrada_status_utc": "2026-09-01"}]
    report = audit([], source, {"rows": []}, [], {"globocorp:sem_mapa": 1})
    assert report["balanced"]
    assert not report["identity_approval_performed"]
    assert report["coverage_by_origin"]["globocorp"]["unmapped_item_ids"] == [2]
    assert report["coverage_by_origin"]["globocorp"]["unmapped_items_with_dated_entry"] == 1


def test_unexplained_loss_blocks_publication():
    with pytest.raises(ValueError, match="reconciliacao"):
        audit([], [{"item_id": 2}], {"rows": []}, [], {})


def test_unknown_published_item_blocks_publication():
    with pytest.raises(ValueError, match="fora da origem/mapa"):
        audit([], [{"item_id": 2}], {"rows": []},
              [{"item_id": 2, "ambiente_origem": "globocorp"}], {})


def test_coverage_is_recomputed_after_mapping_correction():
    source = [{"item_id": 2}]
    mapping = {"rows": [{"viu2_item_id": 1, "globocorp_item_id": 2}]}
    result = audit([], source, mapping,
                   [{"item_id": 2, "ambiente_origem": "globocorp"}], {})
    assert result["coverage_by_origin"]["globocorp"]["unmapped_items"] == 0
    assert result["coverage_by_origin"]["globocorp"]["published_items"] == 1
