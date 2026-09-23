"""Enrich a private draft with event-time labels and explicitly dated context."""

from collections import Counter

from monday_comum.escopo_sla import ler_input
from sls_orcamento_ppd.utils.time import event_timestamp, parse_timestamp

from .reconciliation import data_object, status_index

LABEL_RULES_VERSION = "historical-labels-v2"


def event_label(data):
    value = data.get("value")
    if not isinstance(value, dict):
        return None
    label = value.get("label")
    text = label.get("text") if isinstance(label, dict) else label
    return " ".join(text.split()) if isinstance(text, str) and text.strip() else None


def enrich_passages(candidate, records, snapshots, current_labels, *, input_column=None):
    events = {}
    schema = []
    for record in records:
        key = (str(record["account_id"]), str(record["id"]))
        if key in events:
            raise ValueError("Evento duplicado no enriquecimento")
        events[key] = record
        data = data_object(record["data"])
        if data.get("column_id") == "status_19" and record["event"] not in {
            "update_column_value", "batch_change_pulses_column_value",
        }:
            schema.append((str(record["account_id"]), parse_timestamp(record["created_at"]), str(record["id"])))
    context = {}
    for snap in snapshots:
        key = (str(snap["board_id"]), str(snap["item_id"]))
        if key in context:
            raise ValueError("Cadastro duplicado")
        context[key] = snap
    rows = []
    for passage in candidate["passages"]:
        start = parse_timestamp(passage["entrada_status_utc"])
        end = parse_timestamp(passage["saida_status_utc"]) if passage["saida_status_utc"] else None
        labels_at_start, supporting_labels = set(), set()
        for event_id in passage["supporting_event_ids"]:
            record = events[(passage["source_account_id"], event_id)]
            data = data_object(record["data"])
            item_ids = data.get("pulse_ids", [data.get("pulse_id", data.get("item_id"))])
            if passage["source_item_id"] not in {str(i) for i in item_ids}:
                raise ValueError("Linhagem não corresponde ao item")
            if data.get("column_id") != "status_19":
                raise ValueError("Linhagem não corresponde à coluna")
            if status_index(data.get("value")) != passage["status_index"]:
                continue  # An unknown batch can corroborate a known individual.
            label = event_label(data)
            if label is not None:
                supporting_labels.add(label)
                at, _ = event_timestamp(data, record.get("created_at"))
                if at == start:
                    labels_at_start.add(label)
        quality = ("label_observed_at_start" if len(labels_at_start) == 1 else
                   "conflicting_start_labels" if labels_at_start else "historical_label_unavailable")
        label = next(iter(labels_at_start)) if len(labels_at_start) == 1 else None
        snap = context.get((passage["source_board_id"], passage["source_item_id"]))
        schema_ids = [key for account, at, key in schema
                      if account == passage["source_account_id"] and start <= at and (end is None or at < end)]
        # Only the proven closing event can supply the previous label. Never
        # infer it from the current board or from a nearby timestamp.
        exit_labels, exit_ids = set(), []
        if end is not None:
            for event_id in passage.get("end_event_ids", []):
                record = events[(passage["source_account_id"], event_id)]
                data = data_object(record["data"])
                item_ids = data.get("pulse_ids", [data.get("pulse_id", data.get("item_id"))])
                if (passage["source_item_id"] not in {str(i) for i in item_ids}
                        or data.get("column_id") != "status_19"
                        or (data.get("board_id") is not None
                            and str(data["board_id"]) != passage["source_board_id"])):
                    raise ValueError("Linhagem de saída incompatível")
                at, _ = event_timestamp(data, record.get("created_at"))
                previous = data.get("previous_value")
                if at != end or status_index(previous) != passage["status_index"]:
                    continue
                recovered = event_label({"value": previous})
                if recovered:
                    exit_labels.add(recovered)
                    exit_ids.append(event_id)
        if not labels_at_start and exit_labels:
            if len(exit_labels | supporting_labels) > 1:
                quality = "conflicting_exit_labels"
            elif schema_ids:
                quality = "exit_label_requires_schema_review"
            else:
                label = next(iter(exit_labels))
                quality = "label_observed_at_exit_previous_value"
        rows.append({
            **passage, "status_nome": label, "status_label_quality": quality,
            "status_label_changed_in_support": len(supporting_labels) > 1,
            "status_nome_no_cadastro": current_labels.get(passage["status_index"]),
            "schema_event_ids_during_passage": sorted(schema_ids),
            "label_rules_version": LABEL_RULES_VERSION,
            "label_exit_evidence_ids": sorted(exit_ids),
            "projeto_nome": snap["item_name"] if snap else None,
            "tipo_input": ler_input(input_column, snap["raw_data"]) if snap and input_column else None,
            "tipo_input_verificado": bool(snap and input_column),
            "marca_original": snap.get("marca") if snap else None,
            "talento_original": snap.get("talento") if snap else None,
            "pessoas_cadastro": snap.get("pessoas_json", []) if snap else None,
            "cadastro_referencia_utc": snap["snapshot_at"].isoformat() if snap else None,
            "attribute_source": "snapshot_at_capture" if snap else "unavailable",
            "sla_approved": False,
        })
    return {
        "summary": {
            "candidate_passages": len(rows),
            "label_quality": dict(Counter(r["status_label_quality"] for r in rows)),
            "passages_without_context": sum(r["attribute_source"] == "unavailable" for r in rows),
            "items_without_context": len({(r["source_account_id"], r["source_board_id"], r["source_item_id"])
                                          for r in rows if r["attribute_source"] == "unavailable"}),
            "passages_with_schema_event": sum(bool(r["schema_event_ids_during_passage"]) for r in rows),
            "passages_with_label_change_in_support": sum(r["status_label_changed_in_support"] for r in rows),
            "release_ready": False, "public_contract_compatible": False,
        },
        "passages": rows, "gaps": candidate["gaps"], "calendar": candidate["calendar"],
        "limitations": ["Labels use start evidence or an exact, nonconflicting closing-event previous value; never current board labels.",
                        "Context is capture-time, not historical; raw brand/talent are not eligibility-approved.",
                        "Schema events are review flags, not proven label changes.",
                        "Current public contract requires durations for observed rows and only one open interval; "
                        "this draft preserves known starts with unknown durations and gaps. A versioned contract is required."],
    }
