"""Candidate status observations with lineage. Never edits raw data or computes SLA."""

from collections import Counter, defaultdict

from sls_orcamento_ppd.utils.time import event_timestamp

from .reconciliation import audit_status_batches, data_object, status_index


def build_observations(records, *, account_id, board_id, column_id="status_19"):
    audit_status_batches(records, column_id)  # Reject duplicate events / malformed batches.
    groups = defaultdict(list)
    schema_events = []
    for record in records:
        if str(record["account_id"]) != str(account_id):
            raise ValueError("Observações exigem uma conta de origem")
        data = data_object(record["data"])
        if data.get("column_id") != column_id:
            continue
        kind = record["event"]
        if kind == "update_column_value":
            item = data.get("pulse_id", data.get("item_id"))
            if item is None:
                raise ValueError("Evento individual sem item")
            items = [item]
        elif kind == "batch_change_pulses_column_value":
            items = data["pulse_ids"]
        else:
            schema_events.append(str(record["id"]))
            continue
        action = data.get("action_record_uuid")
        if action is not None and (not isinstance(action, str) or not action.strip()):
            raise ValueError("Identificador de ação inválido")
        # Events without an action UUID must not be collapsed on time/status alone.
        operation = ("action", action) if action else ("event", str(record["id"]))
        at, timestamp_source = event_timestamp(data, record.get("created_at"))
        for item in items:
            groups[(str(item), operation)].append({
                "event_id": str(record["id"]), "kind": kind,
                "status_index": status_index(data.get("value")),
                "event_at_utc": at.isoformat(), "timestamp_source": timestamp_source,
            })
    rows = []
    for (item, operation), sources in sorted(groups.items()):
        sources = sorted(sources, key=lambda s: s["event_id"])
        singles = [s for s in sources if s["kind"] == "update_column_value"]
        indices = {s["status_index"] for s in sources if s["status_index"] is not None}
        # An unknown individual cannot be replaced with a batch guess.
        unknown_individual = any(s["status_index"] is None for s in singles)
        reasons = []
        if operation[0] == "event":
            reasons.append("missing_action_uuid")
        if len(indices) != 1 or unknown_individual:
            reasons.append("unknown_or_conflicting_status")
        timestamps = {s["event_at_utc"] for s in (singles or sources)}
        if len(timestamps) != 1:
            reasons.append("conflicting_timestamps")
        rows.append({
            "source_account_id": str(account_id), "source_board_id": str(board_id),
            "source_item_id": item, "operation_kind": operation[0],
            "operation_id": operation[1],
            "status_index": next(iter(indices)) if len(indices) == 1 and not unknown_individual else None,
            "event_at_utc": next(iter(timestamps)) if len(timestamps) == 1 else None,
            "evidence_kind": "individual" if singles else "batch_explicit_or_unknown",
            "review_reasons": reasons, "sources": sources, "sla_approved": False,
        })
    return {
        "summary": {
            "candidate_observations": len(rows),
            "individual_backed": sum(r["evidence_kind"] == "individual" for r in rows),
            "batch_only_explicit": sum(r["evidence_kind"] != "individual" and
                                       r["status_index"] is not None for r in rows),
            "batch_only_unknown": sum(r["evidence_kind"] != "individual" and
                                      r["status_index"] is None for r in rows),
            "review_reasons": dict(Counter(reason for r in rows for reason in r["review_reasons"])),
            "status_schema_events_to_review": len(schema_events),
            "release_ready": False,
        },
        "observations": rows, "status_schema_event_ids": sorted(schema_events),
        "limitation": "Candidate observations, not SLA intervals. Batch-only timestamps and historical "
                      "status labels require review. No cutoff, duration, context filter or account merge.",
    }
