from datetime import UTC, date, datetime

from sls_orcamento_ppd.services.load import compact_snapshots


def row(item, day, status="Entrada", raw=None):
    return {
        "item_id": item,
        "board_id": 1,
        "snapshot_at": datetime(2026, 9, day, 9, tzinfo=UTC),
        "snapshot_date": date(2026, 9, day),
        "status_text": status,
        "raw_data": raw or {"column_values": [{"id": "x", "text": str(day)}]},
    }


def test_keeps_versions_and_latest_observation_only():
    rows = [row(1, 1), row(1, 2), row(1, 3, "Aguardando Feedback"), row(1, 4, "Aguardando Feedback"),
            row(1, 5, "Aguardando Feedback"), row(2, 1)]
    compacted = compact_snapshots(rows)
    kept = sorted((r["item_id"], r["snapshot_date"].day) for r in compacted)
    # Item 1: version from day 1, version from day 3, latest observation on day 5.
    assert kept == [(1, 1), (1, 3), (1, 5), (2, 1)]


def test_raw_payload_stays_only_on_latest_row():
    compacted = {(r["item_id"], r["snapshot_date"].day): r for r in compact_snapshots(
        [row(1, 1), row(1, 2, "Em Elaboração"), row(1, 3, "Em Elaboração")])}
    assert compacted[(1, 1)]["raw_data"] == {}
    assert compacted[(1, 2)]["raw_data"] == {}
    assert compacted[(1, 3)]["raw_data"] == {"column_values": [{"id": "x", "text": "3"}]}


def test_raw_only_changes_do_not_create_versions():
    # Raw columns the rules do not version (e.g. a new board column) keep one version.
    rows = [row(1, 1, raw={"a": 1}), row(1, 2, raw={"a": 2}), row(1, 3, raw={"a": 3})]
    assert [r["snapshot_date"].day for r in compact_snapshots(rows)] == [1, 3]


def test_compaction_is_idempotent():
    rows = [row(1, d, "Entrada" if d < 3 else "Encerrado") for d in range(1, 8)] + [row(2, 1)]
    once = compact_snapshots(rows)
    assert compact_snapshots(once) == once
