"""Offline candidate passages. Unknown evidence interrupts, never bridges, a visit."""

from collections import Counter, defaultdict

from sls_orcamento_ppd.rules.business_time import BusinessCalendar
from sls_orcamento_ppd.utils.time import parse_timestamp


def build_passages(document):
    calendar = BusinessCalendar("America/Sao_Paulo")
    grouped, seen = defaultdict(list), set()
    for observation in document["observations"]:
        item = tuple(observation[k] for k in
                     ("source_account_id", "source_board_id", "source_item_id"))
        identity = (*item, observation["operation_kind"], observation["operation_id"])
        if identity in seen:
            raise ValueError("Observação duplicada")
        seen.add(identity)
        grouped[item].append(observation)
    passages, gaps = [], []

    def lineage(observations):
        return sorted({s["event_id"] for o in observations for s in o["sources"]})

    for item, observations in sorted(grouped.items()):
        scope = dict(zip(("source_account_id", "source_board_id", "source_item_id"), item, strict=True))
        if any(o["event_at_utc"] is None for o in observations):
            # Cannot locate the gap: no durations for this source item.
            gaps.append({**scope, "reason": "unlocated_timestamp_gap",
                         "event_at_utc": None, "event_ids": lineage(observations)})
            continue
        by_time = defaultdict(list)
        for observation in observations:
            by_time[parse_timestamp(observation["event_at_utc"])].append(observation)
        current = None
        visits = Counter()

        def close(scope, current, end, closing, quality):
            if current is None:
                return
            start = parse_timestamp(current["entrada_status_utc"])
            duration = (end - start).total_seconds() / 3600 if end is not None else None
            passages.append({
                **scope, **current, "saida_status_utc": end.isoformat() if end else None,
                "duracao_horas": round(duration, 3) if duration is not None else None,
                "duracao_horas_uteis": round(calendar.hours(start, end), 3) if end else None,
                "quality": quality, "end_event_ids": lineage(closing),
                "sla_approved": False,
            })

        for at, evidence in sorted(by_time.items()):
            indices = {o["status_index"] for o in evidence}
            blocking = any(set(o["review_reasons"]) - {"missing_action_uuid"} for o in evidence)
            if len(indices) != 1 or None in indices or blocking:
                close(scope, current, None, evidence, "interrupted_by_evidence_gap")
                current = None
                gaps.append({**scope, "reason": "unknown_or_simultaneous_conflicting_status",
                             "event_at_utc": at.isoformat(), "event_ids": lineage(evidence)})
                continue
            index = next(iter(indices))
            if current is not None and current["status_index"] == index:
                current["supporting_event_ids"] = sorted(set(current["supporting_event_ids"]) |
                                                         set(lineage(evidence)))
                continue
            close(scope, current, at, evidence, "observed_closed_candidate")
            visits[index] += 1
            current = {
                "status_index": index, "entrada_status_utc": at.isoformat(),
                "observed_visit_number": visits[index],
                "supporting_event_ids": lineage(evidence),
            }
        close(scope, current, None, [], "no_observed_exit")
    return {
        "summary": {
            "source_items": len(grouped), "candidate_passages": len(passages),
            "passages_with_duration": sum(p["duracao_horas"] is not None for p in passages),
            "quality": dict(Counter(p["quality"] for p in passages)),
            "gap_records": len(gaps), "release_ready": False,
        },
        "passages": passages, "gaps": gaps, "calendar": calendar.snapshot(),
        "status_schema_event_ids": document.get("status_schema_event_ids", []),
        "limitations": ["Draft only; not the public SLA contract or KPI-approved data.",
                        "Historical status labels/schema and migration boundary remain unvalidated.",
                        "No first Entrada inferred, no current-time closure, no cross-account merge.",
                        "Visit count means observed visits only; gaps can hide returns.",
                        "All observations remain in the input artifact, including unordered items."],
    }
