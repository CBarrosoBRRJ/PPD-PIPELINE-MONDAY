"""Freeze an explicit matching policy without claiming per-item human review.

Private map, one row per selected pair. Does not grant KPI eligibility, infer
migration times, delete unmatched records, or alter the approved-map contract.
"""

from collections import Counter
from uuid import UUID, uuid5

POLICY = "unique-name-entry-date-no-link-conflict-v1"
NAMESPACE = UUID("a90b14f5-4910-44be-a218-e09aa4779af7")


def select_identity(report, old_ids, new_ids):
    old_ids, new_ids = set(map(str, old_ids)), set(map(str, new_ids))
    rows, seen_old, seen_new = [], set(), set()
    candidates = report["candidates"]
    candidate_keys = set()
    for candidate in candidates:
        old, new = candidate["viu2_item_id"], candidate["globocorp_item_id"]
        if old not in old_ids or new not in new_ids:
            raise ValueError("Identidade: candidato fora dos contextos")
        if (old, new) in candidate_keys:
            raise ValueError("Identidade: candidato duplicado")
        candidate_keys.add((old, new))
        if candidate["unique_name_and_entry_date"] is not True or candidate["conflicting_link_fields"]:
            continue
        if not candidate["same_name"] or len(candidate["matching_fields"]) < 2:
            raise ValueError("Identidade: evidência complementar ausente")
        if old in seen_old or new in seen_new:
            raise ValueError("Identidade: relação não é um para um")
        if not old.isdecimal() or not new.isdecimal() or min(int(old), int(new)) <= 0:
            raise ValueError("Identidade: ID inválido")
        seen_old.add(old)
        seen_new.add(new)
        rows.append({
            "projeto_id": str(uuid5(NAMESPACE, "viu2:5890468:18393336134:" + old)),
            "viu2_account_id": "5890468", "viu2_board_id": "18393336134", "viu2_item_id": old,
            "globocorp_account_id": "21453629", "globocorp_board_id": "18429499488", "globocorp_item_id": new,
            "identity_quality": "selected_by_user_accepted_policy",
            "individual_human_review": False, "policy": POLICY,
            "matching_fields": candidate["matching_fields"],
            "different_fields": candidate["different_fields"],
            "unique_link_evidence": candidate["unique_link_evidence"],
            "sla_approved": False,
        })
    excluded = []
    for old in sorted(old_ids - seen_old):
        has_conflict = any(c["viu2_item_id"] == old and c["unique_name_and_entry_date"]
                           and c["conflicting_link_fields"] for c in candidates)
        excluded.append({"viu2_item_id": old, "reason": "conflicting_links" if has_conflict
                         else "no_unique_name_and_entry_date", "raw_preserved": True})
    return {
        "version": "selected-identity-v1", "policy": POLICY,
        "summary": {"selected_pairs": len(rows), "excluded_viu2_context_items": len(excluded),
                    "unlinked_globocorp_context_items": len(new_ids - seen_new),
                    "exclusion_reasons": dict(Counter(r["reason"] for r in excluded))},
        "rows": sorted(rows, key=lambda r: r["viu2_item_id"]), "excluded_viu2": excluded,
        "unlinked_globocorp": sorted(new_ids - seen_new),
        "limitations": ["Matching policy accepted by user, not an authoritative migration map.",
                        "Coverage is limited to captured contexts, not all historical items.",
                        "No inference that unlinked globocorp items are new or invalid.",
                        "No transfer time or duration across environments is approved."],
    }
