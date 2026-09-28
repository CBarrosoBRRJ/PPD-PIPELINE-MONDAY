import json

from ..models.schemas import DEFINITIONS

SNAPSHOT = "bronze_monday_item_snapshot_raw"
# Observation times and the raw payload do not define a new version of an item.
_NOT_VERSION = {"snapshot_at", "snapshot_date", "raw_data"}


def merge_rows(old, new, table):
    keys = DEFINITIONS[table][0].split(",")
    merged = {tuple(row[k] for k in keys): row for row in old}
    for row in new:
        merged[tuple(row[k] for k in keys)] = row
    return list(merged.values())


def compact_snapshots(rows):
    """Keep one row per change of the typed fields, plus each item's latest observation.

    Daily snapshots are mostly identical copies; storing all of them made the state grow
    with items x days. The raw payload stays only on the latest row, which is the one the
    rules read; the complete daily payload is archived in GCS before each commit.
    Idempotent: compacting an already compacted history returns the same rows.
    """
    by_item = {}
    for row in rows:
        by_item.setdefault(row["item_id"], []).append(row)
    result = []
    for item_rows in by_item.values():
        item_rows.sort(key=lambda r: r["snapshot_at"])
        previous = None
        for i, row in enumerate(item_rows):
            signature = json.dumps(
                {k: v for k, v in row.items() if k not in _NOT_VERSION},
                sort_keys=True,
                default=str,
            )
            last = i == len(item_rows) - 1
            if signature != previous or last:
                result.append(row if last else {**row, "raw_data": {}})
            previous = signature
    return result
