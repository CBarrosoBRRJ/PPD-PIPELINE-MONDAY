"""Compare pinned published v7 with local rebuild without rewriting either."""

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from audit_kpi_candidate import checked, reconstruct
from monday_sla_orcamento.kpi_etapa import decision
from monday_sla_orcamento.publication import canonical, fingerprint
from sls_orcamento_ppd.models.bq_consumption import FIELDS
from sls_orcamento_ppd.rules.business_time import BusinessCalendar

PUBLISHED_SHA = "e892c698bf6f5656f47b9beee3e3a0fdb7bb72904de4105d43c1a035eb5f0e6f"
PUBLISHED_FINGERPRINT = "6c33244f4fff85a9f5ebd0e09685aed8a6bf746eb0f5d8df92e7b91363447987"


def normalize_source(source):
    result = dict(source)
    for spec in FIELDS.split():
        key, kind = spec.split(":")
        value = result.get(key)
        if value is None:
            continue
        if kind in {"time", "localtime"}:
            value = datetime.fromisoformat(value.replace(" UTC", "+00:00").replace("Z", "+00:00"))
            if kind == "time":
                if value.utcoffset() is None:
                    raise ValueError("Timestamp without zone")
                value = value.astimezone(UTC)
            elif value.tzinfo is not None:
                raise ValueError("Local datetime with zone")
            value = value.isoformat(timespec="microseconds")
        result[key] = value
    return result


def main():
    published = [json.loads(line) for line in checked(
        "C:/Users/CCMB/Downloads/consolidado-publicado-v7.ndjson.gz", PUBLISHED_SHA).splitlines()]
    if fingerprint(published) != PUBLISHED_FINGERPRINT:
        raise ValueError("Published receipt mismatch")
    actual = {r["interval_id"]: r for r in canonical(published)}
    local = {r["interval_id"]: r for r in canonical(reconstruct())}
    if actual.keys() != local.keys():
        raise ValueError("Interval key sets differ")
    changed, source_changed, material = Counter(), Counter(), Counter()
    for key, row in actual.items():
        for field in row:
            if row[field] != local[key][field]:
                changed[field] += 1
                if field != "registro_origem_json":
                    material[field] += 1
                    continue
                left, right = json.loads(row[field]), json.loads(local[key][field])
                source_changed.update(k for k in left.keys() | right.keys() if left.get(k) != right.get(k))
                if normalize_source(left) != normalize_source(right):
                    material[field] += 1
    calendar = BusinessCalendar("America/Sao_Paulo")
    counts = Counter()
    decision_changes = 0
    for key, row in actual.items():
        verdict = decision(row, calendar)
        decision_changes += verdict != decision(local[key], calendar)
        if verdict["elegivel_kpi_etapa_candidato"]:
            counts[row["ambiente_origem"]] += 1
    report = {"rows": len(actual), "published_fingerprint_verified": True,
              "changed_fields": dict(changed), "source_changed_fields": dict(source_changed),
              "material_differences": dict(material), "candidate_decision_changes": decision_changes,
              "candidates_on_published": dict(counts), "cloud_modified": False,
              "kpi_approved": False}
    with Path("runtime/validation/kpi_snapshot_reconciliation_20260923.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))
    if material or decision_changes:
        raise SystemExit("Reconciliation blocked")


if __name__ == "__main__":
    main()
