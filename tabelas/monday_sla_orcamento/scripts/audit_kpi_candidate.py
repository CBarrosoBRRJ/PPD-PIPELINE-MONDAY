"""Pinned, offline v7 reconstruction and stage-KPI coverage. No cloud writes."""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from historico_viu2.eligibility import frozen_inputs
from monday_sla_orcamento.consolidation import build
from monday_sla_orcamento.kpi_etapa import VERSION, decision
from monday_sla_orcamento.publication import HISTORY_SHA, MAP_SHA, fingerprint
from sls_orcamento_ppd.models.bq_consumption import FIELDS
from sls_orcamento_ppd.rules.business_time import BusinessCalendar


def checked(path, expected):
    blob = Path(path).read_bytes()
    if hashlib.sha256(blob).hexdigest() != expected:
        raise ValueError("KPI audit: source checksum mismatch")
    return gzip.decompress(blob)


def reconstruct(*, legacy=True):
    old = [json.loads(line) for line in checked(
        "runtime/validation/viu2_review_labels_v2/coordinator_source.ndjson.gz", HISTORY_SHA).splitlines()]
    mapping = json.loads(checked("runtime/validation/selected_identity_20260922_v1/selected_identity.json.gz", MAP_SHA))
    new = []
    for line in checked("C:/Users/CCMB/Downloads/globocorp-000000000000.json.gz",
                        "e2e7f226acf9e4a448267e1b2915c8a736d821785c99d0b46efdb7dd977daff8").splitlines():
        raw = json.loads(line)
        row = {}
        for field in FIELDS.split():
            name, kind = field.split(":")
            value = raw.get(name)
            if value is not None:
                if kind in {"id", "int"}:
                    value = int(value)
                elif kind == "num":
                    value = float(value)
                elif kind == "time":
                    value = value.replace(" UTC", "+00:00")
            row[name] = value
        new.append(row)
    archive = Path("runtime/archives/viu2_18393336134_20260921")
    inputs = frozen_inputs(lambda name: (archive / name).read_bytes())
    rows, _ = build(old, new, mapping, old_inputs=inputs)
    if legacy:
        from monday_sla_orcamento.analysis_duration import FIELDS as analysis_fields
        from monday_sla_orcamento.consumo import FIELDS as consumption_fields
        from monday_sla_orcamento.estimates import FIELDS as estimate_fields
        from monday_sla_orcamento.trajectory import FIELDS as trajectory_fields
        for row in rows:
            for key in {**consumption_fields, **trajectory_fields, **estimate_fields, **analysis_fields}:
                row.pop(key)
            row.update(versao_contrato="sla-consolidado-evidencias-v2",
                       validacao_negocio="pendente", elegivel_comparacao=False)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = reconstruct()
    calendar = BusinessCalendar("America/Sao_Paulo")
    results = [(row, decision(row, calendar)) for row in rows]
    by_origin = {}
    for origin in ("viu2", "globocorp"):
        subset = [(r, d) for r, d in results if r["ambiente_origem"] == origin]
        allowed = [r for r, d in subset if d["elegivel_kpi_etapa_candidato"]]
        by_origin[origin] = {
            "passagens_total": len(subset), "passagens_candidatas": len(allowed),
            "projetos_candidatos": len({r["item_id"] for r in allowed}),
            "motivos_bloqueio_nao_aditivos": dict(Counter(m for _, d in subset for m in d["motivos"])),
        }
    enriched_blob = Path("runtime/validation/viu2_passages_enriched_labels_v2.json").read_bytes()
    enriched = json.loads(enriched_blob)
    support_conflicts = sum(bool(p["status_label_changed_in_support"]) for p in enriched["passages"])
    if support_conflicts:
        raise ValueError("KPI audit: conflicting support labels require review")
    report = {"policy": VERSION, "production_changed": False, "kpi_approved": False,
              "support_label_conflicts": support_conflicts,
              "enriched_sha256": hashlib.sha256(enriched_blob).hexdigest(),
              "v7_fingerprint_reconstructed": fingerprint(rows), "rows": len(rows),
              "calendar_version": calendar.version, "by_origin": by_origin}
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
