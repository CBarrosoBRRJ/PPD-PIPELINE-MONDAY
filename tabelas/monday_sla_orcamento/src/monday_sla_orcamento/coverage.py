"""Read-only coverage evidence rebuilt for every consolidation, never identity approval."""

from collections import Counter


def audit(old_rows, new_rows, mapping, published, excluded):
    sources = {"viu2": old_rows, "globocorp": new_rows}
    source_count = sum(len(rows) for rows in sources.values())
    if source_count != len(published) + sum(excluded.values()):
        raise ValueError("Consolidacao: reconciliacao de passagens divergente")
    coverage = {}
    for origin, rows in sources.items():
        mapped = {int(pair[origin + "_item_id"]) for pair in mapping["rows"]}
        present = {int(row["item_id"]) for row in rows}
        retained = {int(row["item_id"]) for row in published
                    if row["ambiente_origem"] == origin}
        if not retained <= present & mapped:
            raise ValueError("Consolidacao: item publicado fora da origem/mapa")
        missing = present - mapped
        coverage[origin] = {
            "source_items": len(present),
            "published_items": len(retained),
            "mapped_not_published_items": len((present & mapped) - retained),
            "unmapped_items": len(missing),
            # IDs remain in the private publication report, not general logs.
            "unmapped_item_ids": sorted(missing),
            "unmapped_items_with_dated_entry": len({
                int(row["item_id"]) for row in rows
                if int(row["item_id"]) in missing
                and (row.get("status_nome") or "").strip().casefold() == "entrada"
                and row.get("entrada_status_utc") is not None
            }),
        }
    return {
        "rule": "reconciliacao-cobertura-v1",
        "source_rows": source_count,
        "published_rows": len(published),
        "excluded_rows": sum(excluded.values()),
        "balanced": True,
        "coverage_by_origin": coverage,
        "published_rows_by_origin": dict(Counter(r["ambiente_origem"] for r in published)),
        "identity_approval_performed": False,
    }
