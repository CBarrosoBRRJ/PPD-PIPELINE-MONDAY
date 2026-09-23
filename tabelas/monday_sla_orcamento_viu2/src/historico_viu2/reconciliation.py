"""Read-only reconciliation of batch and individual status evidence.

Matching action UUID + item is evidence of the same operation, not permission to
invent missing per-item transitions. This audit does not transform any event.
"""

import json
from collections import Counter, defaultdict


def profile_item_review(records, context_item_ids, *, account_id, board_id,
                        column_id="status_19"):
    """Private triage by source item, not an eligibility or completeness verdict."""
    if any(str(r["account_id"]) != str(account_id) for r in records):
        raise ValueError("Triagem exige uma conta de origem")
    audit = audit_status_batches(records, column_id)
    context = {str(i) for i in context_item_ids}
    pending = defaultdict(Counter)
    individual = Counter()
    batch_items = set()
    for reference in audit["pending_references"]:
        pending[reference["item_id"]][reference["reason"]] += 1
    for record in records:
        data = data_object(record["data"])
        if data.get("column_id") != column_id:
            continue
        if record["event"] == "batch_change_pulses_column_value":
            batch_items.update(str(i) for i in data["pulse_ids"])
        elif record["event"] == "update_column_value":
            item = data.get("pulse_id", data.get("item_id"))
            if item is not None:
                individual[str(item)] += 1
    rows = []
    for item in sorted(context | set(individual) | batch_items):
        reasons = dict(sorted(pending[item].items()))
        group = ("batch_review_required" if reasons else
                 "individual_evidence_no_pending_batch" if individual[item] else
                 "no_individual_status_evidence")
        rows.append({
            "source_account_id": str(account_id), "source_board_id": str(board_id),
            "source_item_id": item, "in_current_context": item in context,
            "individual_status_events": individual[item],
            "batch_review_reasons": reasons, "triage_group": group,
            "sla_approved": False,
        })
    return {
        "summary": {
            "items": len(rows), "context_items": len(context),
            "items_outside_current_context": sum(not r["in_current_context"] for r in rows),
            "groups": dict(Counter(r["triage_group"] for r in rows)),
            "release_ready": False,
        },
        "items": rows,
        "limitation": "Source item is not a reconciled project. No pending batch does not prove complete history. "
                      "No cutoff, durations, inferred transitions or cross-account matching are applied.",
    }


def data_object(value):
    result = json.loads(value) if isinstance(value, str) else value
    if not isinstance(result, dict):
        raise ValueError("Reconciliação: conteúdo de evento inválido")
    return result


def status_index(value):
    if not isinstance(value, dict):
        return None
    label = value.get("label")
    index = label.get("index", value.get("index")) if isinstance(label, dict) else value.get("index")
    return str(index) if index is not None else None


def audit_status_batches(records, column_id="status_19"):
    individual, batches, events_seen = defaultdict(list), [], set()
    counts = Counter()
    for record in records:
        identity = (str(record["account_id"]), str(record["id"]))
        if identity in events_seen:
            raise ValueError("Reconciliação: evento repetido na entrada")
        events_seen.add(identity)
        data = data_object(record["data"])
        if data.get("column_id") != column_id:
            continue
        counts[record["event"]] += 1
        action = data.get("action_record_uuid")
        if record["event"] == "update_column_value" and action:
            item = data.get("pulse_id", data.get("item_id"))
            if item is not None:
                individual[(str(record["account_id"]), action, str(item))].append(data)
        elif record["event"] == "batch_change_pulses_column_value":
            batches.append((record, data))
    categories, details = Counter(), []
    for record, data in batches:
        items = data.get("pulse_ids")
        if not isinstance(items, list) or any(type(i) not in (int, str) for i in items):
            raise ValueError("Reconciliação: itens do lote inválidos")
        if len({str(i) for i in items}) != len(items):
            raise ValueError("Reconciliação: item repetido no lote")
        batch_index = status_index(data.get("value"))
        for item in items:
            matches = individual.get((str(record["account_id"]), data.get("action_record_uuid"), str(item)), [])
            indices = {status_index(m.get("value")) for m in matches}
            if not matches:
                category = "missing_individual_with_value" if batch_index is not None else "missing_individual_without_value"
            elif batch_index is None:
                category = "individual_present_batch_value_unknown"
            elif indices == {batch_index}:
                category = "same_action_item_and_status"
            else:
                category = "status_conflict_or_unknown"
            categories[category] += 1
            if category != "same_action_item_and_status":
                details.append({"event_id": str(record["id"]), "item_id": str(item), "reason": category})
    return {
        "raw_events_checked": len(records),
        "status_event_types": dict(counts),
        "batch_events": len(batches),
        "batch_item_references": sum(categories.values()),
        "categories": dict(categories),
        "review_required": bool(details),
        "pending_references": details,
        "limitation": "Audit only; does not create, discard or certify status transitions.",
    }


def profile_batch_coverage(records, context_item_ids, column_id="status_19"):
    """Quantify evidence gaps without interpreting absent values or inventing events."""
    audit = audit_status_batches(records, column_id)
    context = {str(item) for item in context_item_ids}
    by_category = defaultdict(set)
    for reference in audit["pending_references"]:
        by_category[reference["reason"]].add(reference["item_id"])
    shapes = Counter()
    for record in records:
        data = data_object(record["data"])
        if record["event"] != "batch_change_pulses_column_value" or data.get("column_id") != column_id:
            continue
        if "value" not in data:
            shapes["value_field_absent"] += 1
        elif data["value"] is None:
            shapes["value_explicit_null"] += 1
        elif status_index(data["value"]) is not None:
            shapes["explicit_status_index"] += 1
        else:
            shapes["unrecognized_value"] += 1
    missing = set().union(*(items for category, items in by_category.items()
                           if category.startswith("missing_individual")))
    return {
        "batch_value_shapes": dict(shapes),
        "review_categories": {
            category: {"distinct_items": len(items),
                       "in_current_context": len(items & context),
                       "outside_current_context": len(items - context)}
            for category, items in sorted(by_category.items())
        },
        "items_without_individual_counterpart": len(missing),
        "items_without_individual_counterpart_in_context": len(missing & context),
        "categories_overlap": True,
        "release_ready": False,
        "limitation": "Absent value is unknown, not a proved clear; current context is not historical coverage.",
    }
