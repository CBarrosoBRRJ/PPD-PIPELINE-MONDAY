"""Read-only diagnostic: distinct evidenced statuses of matched closed projects.

Previous values prove a prior state, not its start time or duration. This report
does not publish SLA or approve identities. All artifacts remain private.
"""
import gzip
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from historico_viu2.observations import build_observations
from historico_viu2.reconciliation import data_object, status_index


def main():
    root = Path("runtime")
    context_path = root / "validation/project_matching_20260922_v1/globocorp_context.json.gz"
    context_bytes = context_path.read_bytes()
    assert hashlib.sha256(context_bytes).hexdigest() == context_path.with_suffix(".sha256").read_text().strip().split()[0]
    context = json.loads(gzip.decompress(context_bytes))
    matching = json.loads((root / "validation/project_matching_20260922_v3/matching_report.json").read_text(encoding="utf-8"))
    pairs = {r["globocorp_item_id"]: r["viu2_item_id"] for r in matching["candidates"]
             if r["unique_name_and_entry_date"] and not r["conflicting_link_fields"]}
    assert len(pairs) == len(set(pairs.values())) == 4294
    archive = root / "archives/globocorp_status_validation_20260922_v1"
    manifest = json.loads((archive / "manifest.json").read_text())
    assert manifest["status"] == "complete_available_status_history"
    assert manifest["context_sha256"] == hashlib.sha256(context_bytes).hexdigest()
    records = []
    for name in manifest["accepted_log_pages"]:
        raw = (archive / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest["files"][name]["sha256"]
        records.extend(json.loads(gzip.decompress(raw))["response"]["boards"][0]["activity_logs"])
    new_obs = build_observations(records, account_id="21453629", board_id="18429499488")["observations"]
    old_obs = json.loads((root / "validation/viu2_status_observations_20260922_v1.json").read_text(encoding="utf-8"))["observations"]
    previous = {}

    def remember(account, event_id, kind, data):
        # Batch previous_value is not automatically applicable to each item.
        if kind == "update_column_value" and data.get("column_id") == "status_19":
            previous[(account, str(event_id))] = status_index(data.get("previous_value"))

    old_path = root / "archives/viu2_18393336134_20260921/structured/log_monday_viu2.ndjson.gz"
    assert hashlib.sha256(old_path.read_bytes()).hexdigest() == "3cdb2da4afa7881577222fa849b8f99c9f869d886bbca5ab2379ce319747a979"
    with gzip.open(old_path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            remember("5890468", row["event_id"], row["event_type"], data_object(row["data_raw"]))
    for row in records:
        remember("21453629", row["id"], row["event"], data_object(row["data"]))
    by_old, by_new = defaultdict(list), defaultdict(list)
    for row in old_obs:
        by_old[row["source_item_id"]].append(row)
    for row in new_obs:
        by_new[row["source_item_id"]].append(row)
    # Current copied status dictionaries align by index except punctuation in GP.
    # Report counts status codes, not spelling variants or repeated visits.
    groups, excluded = defaultdict(list), []
    current_closed = 0
    for item in context["items"]:
        col = next((c for c in item["column_values"] if c["id"] == "status_19"), None)
        if not col or not col["value"] or json.loads(col["value"]).get("index") != 8:
            continue
        current_closed += 1
        new_id = str(item["id"])
        old_id = pairs.get(new_id)
        obs = by_old[old_id] + by_new[new_id] if old_id else []
        reason = None
        if not old_id:
            reason = "identity_not_selected"
        elif not obs:
            reason = "no_observed_transitions"
        elif any(r["event_at_utc"] is None for r in obs):
            reason = "unknown_timestamp"
        if reason:
            excluded.append({"globocorp_item_id": new_id, "viu2_item_id": old_id, "reason": reason})
            continue
        obs.sort(key=lambda r: r["event_at_utc"])
        last_time = obs[-1]["event_at_utc"]
        if {r["status_index"] for r in obs if r["event_at_utc"] == last_time} != {"8"}:
            excluded.append({"globocorp_item_id": new_id, "viu2_item_id": old_id, "reason": "final_state_unconfirmed"})
            continue
        prior = {r["status_index"] for r in obs if r["event_at_utc"] < last_time}
        targets_only = prior - {None, "8", "5"}
        prior_values = {previous.get((r["source_account_id"], s["event_id"])) for r in obs for s in r["sources"]}
        prior = (prior | prior_values) - {None, "8", "5"}
        groups[len(prior)].append({
            "viu2_item_id": old_id, "globocorp_item_id": new_id,
            "prior_status_indices": sorted(prior), "target_only_count": len(targets_only),
            "previous_value_adds_status": bool(prior - targets_only),
            "unknown_status_evidence": any(r["status_index"] is None for r in obs),
            "final_observed_at": last_time,
        })
    summary = [{"prior_distinct_statuses": n, "projects": len(rows),
                "unknown_status_evidence": sum(r["unknown_status_evidence"] for r in rows),
                "example": sorted(rows, key=lambda r: int(r["globocorp_item_id"]))[0]}
               for n, rows in sorted(groups.items())]
    result = {"context_captured_at": context["captured_at"], "current_closed": current_closed,
              "identity_rule": "unique_name_and_entry_date_without_conflicting_links",
              "count_definition": "distinct observed target or individual previous status; excludes Encerrado and blank; no synthetic dates",
              "limitation": "Observed evidence, not proof of complete lifetime history. Identity matching remains rule-based.",
              "excluded_counts": dict(Counter(r["reason"] for r in excluded)),
              "summary": summary, "projects_by_count": dict(groups), "excluded": excluded}
    assert sum(len(rows) for rows in groups.values()) + len(excluded) == current_closed
    output = root / "validation/closed_trajectory_both_20260922_v1.json"
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k not in ("projects_by_count", "excluded")}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
