"""Cross-account candidate discovery. Never approves or merges source identities."""

import json
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from urllib.parse import urlsplit, urlunsplit


def normalized(value):
    return " ".join(unicodedata.normalize("NFC", str(value or "")).casefold().split())


def field_value(column):
    if column.get("type") == "link":
        raw = column.get("value")
        data = json.loads(raw) if isinstance(raw, str) and raw else raw or {}
        value = data.get("url")
        if not value:
            return ""
        parts = urlsplit(value.strip())
        if parts.scheme not in {"http", "https"} or not parts.netloc:
            return ""
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, parts.query, parts.fragment))
    # Do not compare account-specific people/status/relation IDs.
    return normalized(column.get("display_value") or column.get("text"))


def find_candidates(old_board, old_items, new_board, new_items):
    allowed = {"text", "long_text", "link", "date", "numbers", "dropdown"}
    old_columns = {c["id"]: c for c in old_board["columns"] if c["type"] in allowed}
    new_columns = {c["id"]: c for c in new_board["columns"] if c["type"] in allowed}
    shared = {k: v for k, v in old_columns.items() if k in new_columns and
              v["type"] == new_columns[k]["type"] and normalized(v["title"]) == normalized(new_columns[k]["title"])}

    def prepare(items):
        prepared = {}
        for item in items:
            key = str(item["id"])
            if key in prepared:
                raise ValueError("Item repetido na origem")
            prepared[key] = {"name": normalized(item["name"]), "original_name": item["name"],
                             "values": {c["id"]: field_value(c) for c in item["column_values"] if c["id"] in shared}}
        return prepared

    old, new = prepare(old_items), prepare(new_items)

    def indices(items):
        result = defaultdict(lambda: defaultdict(set))
        for key, item in items.items():
            if item["name"]:
                result["name"][item["name"]].add(key)
            for column, value in item["values"].items():
                if value:
                    result[column][value].add(key)
        return result

    oi, ni = indices(old), indices(new)
    stats, pair_seeds = [], defaultdict(set)
    anchors = {k for k, c in shared.items() if c["type"] == "link" or
               "salesforce" in normalized(c["title"]) or normalized(c["title"]) in {"sf", "link sf"}}
    for field in ["name", *sorted(shared)]:
        common = set(oi[field]) & set(ni[field])
        unique = {v for v in common if len(oi[field][v]) == len(ni[field][v]) == 1}
        stats.append({"field": field, "title": shared[field]["title"] if field in shared else "Projeto",
                      "common_values": len(common), "unique_on_both_sides": len(unique),
                      "old_distinct_values": len(oi[field]), "new_distinct_values": len(ni[field])})
        if field == "name" or field in anchors:
            for value in common:
                if len(oi[field][value]) * len(ni[field][value]) > 100:
                    continue  # Common generic values cannot create unbounded candidate pairs.
                for left in oi[field][value]:
                    for right in ni[field][value]:
                        pair_seeds[(left, right)].add(field)
    # Native IDs are evidence to inspect, not a cross-account identity guarantee.
    for key in set(old) & set(new):
        pair_seeds[(key, key)].add("native_item_id")
    entry_columns = [k for k, c in shared.items() if c["type"] == "date" and
                     normalized(c["title"]) == "data de entrada"]
    name_date_pairs = set()
    if len(entry_columns) == 1:
        entry_column = entry_columns[0]
        def name_date_index(items):
            result = defaultdict(set)
            for key, item in items.items():
                value = (item["name"], item["values"].get(entry_column))
                if all(value):
                    result[value].add(key)
            return result
        left_dates, right_dates = name_date_index(old), name_date_index(new)
        for value in set(left_dates) & set(right_dates):
            if len(left_dates[value]) == len(right_dates[value]) == 1:
                pair = (next(iter(left_dates[value])), next(iter(right_dates[value])))
                name_date_pairs.add(pair)
                pair_seeds[pair].add("unique_name_and_entry_date")
    rows = []
    for (left, right), seeds in sorted(pair_seeds.items()):
        a, b = old[left], new[right]
        matches = [k for k in shared if a["values"].get(k) and a["values"].get(k) == b["values"].get(k)]
        differences = [k for k in shared if a["values"].get(k) and b["values"].get(k) and
                       a["values"][k] != b["values"][k]]
        unique_matches = [k for k in matches if len(oi[k][a["values"][k]]) == len(ni[k][a["values"][k]]) == 1]
        same_name = bool(a["name"] and a["name"] == b["name"])
        strong_anchor = sorted(set(unique_matches) & anchors)
        conflicts = sorted(set(differences) & anchors)
        tier = ("name_and_unique_link" if same_name and strong_anchor and not conflicts else
                "link_with_name_or_link_difference" if strong_anchor else
                "name_and_attributes" if same_name and len(matches) >= 2 else "name_or_id_only")
        rows.append({"viu2_item_id": left, "globocorp_item_id": right,
                     "viu2_name": a["original_name"], "globocorp_name": b["original_name"],
                     "same_name": same_name, "same_native_item_id": left == right,
                     "seed_fields": sorted(seeds), "matching_fields": sorted(matches),
                     "unique_matching_fields": sorted(unique_matches), "different_fields": sorted(differences),
                     "unique_link_evidence": strong_anchor, "conflicting_link_fields": conflicts,
                     "unique_name_and_entry_date": (left, right) in name_date_pairs,
                     "tier": tier, "review_status": "pending", "approved": False})
    strong = [r for r in rows if r["tier"] == "name_and_unique_link"]
    old_degree = Counter(r["viu2_item_id"] for r in strong)
    new_degree = Counter(r["globocorp_item_id"] for r in strong)
    for r in strong:
        if old_degree[r["viu2_item_id"]] != 1 or new_degree[r["globocorp_item_id"]] != 1:
            r["tier"] = "ambiguous_strong_links"
    represented = {r["viu2_item_id"] for r in rows}
    # Test composite keys separately from approval; missing components never match.
    comparison_fields = sorted(
        (s for s in stats if s["field"] != "name" and s["common_values"] >= 5),
        key=lambda s: (-s["common_values"], s["field"]),
    )[:12]
    combo_stats = []
    for size in (1, 2):
        for fields in combinations([s["field"] for s in comparison_fields], size):
            def composite_index(items, selected_fields=fields):
                result = defaultdict(set)
                for key, item in items.items():
                    values = (item["name"], *(item["values"].get(k, "") for k in selected_fields))
                    if all(values):
                        result[values].add(key)
                return result
            left_index, right_index = composite_index(old), composite_index(new)
            common = set(left_index) & set(right_index)
            unique = [value for value in common if len(left_index[value]) == len(right_index[value]) == 1]
            combo_stats.append({
                "fields": ["name", *fields], "unique_pairs": len(unique),
                "ambiguous_values": len(common) - len(unique),
                "disambiguated_repeated_names": sum(len(oi["name"][value[0]]) > 1 or
                                                    len(ni["name"][value[0]]) > 1 for value in unique),
            })
    return {"summary": {"viu2_items": len(old), "globocorp_items": len(new),
                        "native_ids_in_common": len(set(old) & set(new)), "shared_columns": len(shared),
                        "candidate_pairs": len(rows), "tiers": dict(Counter(r["tier"] for r in rows)),
                        "viu2_items_with_candidates": len(represented),
                        "viu2_items_without_candidates": len(old) - len(represented),
                        "unique_name_and_entry_date_pairs": len(name_date_pairs),
                        "name_date_pairs_with_additional_attributes": sum(r["unique_name_and_entry_date"] and
                                                                          len(r["matching_fields"]) >= 2 for r in rows),
                        "name_date_pairs_with_unique_link": sum(r["unique_name_and_entry_date"] and
                                                                bool(r["unique_link_evidence"]) for r in rows),
                        "name_date_pairs_with_link_conflicts": sum(r["unique_name_and_entry_date"] and
                                                                   bool(r["conflicting_link_fields"]) for r in rows),
                        "approved_pairs": 0},
            "field_statistics": stats, "combination_statistics": sorted(combo_stats, key=lambda r: (-r["unique_pairs"], r["fields"])),
            "candidates": rows,
            "limitations": ["Candidates only; no identity approval, mutation or SLA union.",
                            "No fuzzy name matching. Empty values do not match. Mutable statuses/people are excluded.",
                            "Shared columns require same ID, type and normalized title.",
                            "Groups producing over 100 pairs per value are not expanded; lack of candidate is not absence of project."]}
