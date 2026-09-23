"""Offline additive v4 validation from pinned published v7 and verified v3 rules."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from audit_kpi_candidate import checked
from monday_sla_orcamento.consolidation import CONSUMPTION_VERSION as VERSION
from monday_sla_orcamento.consolidation import STAGE_VERSION, validate
from monday_sla_orcamento.consumo import FIELDS, project
from monday_sla_orcamento.kpi_etapa import decision
from monday_sla_orcamento.publication import fingerprint
from reconcile_kpi_snapshot import PUBLISHED_FINGERPRINT, PUBLISHED_SHA
from sls_orcamento_ppd.rules.business_time import BusinessCalendar


def main():
    baseline = [json.loads(line) for line in checked(
        "C:/Users/CCMB/Downloads/consolidado-publicado-v7.ndjson.gz", PUBLISHED_SHA).splitlines()]
    if fingerprint(baseline) != PUBLISHED_FINGERPRINT:
        raise ValueError("Snapshot mismatch")
    calendar = BusinessCalendar("America/Sao_Paulo")
    for row in baseline:
        eligible = decision(row, calendar)["elegivel_kpi_etapa_candidato"]
        row.update(versao_contrato=STAGE_VERSION, elegivel_comparacao=eligible,
                   validacao_negocio="aprovado_etapa_origem_v1" if eligible else "nao_elegivel_etapa_origem_v1")
    before_hash = fingerprint(baseline)
    if before_hash != "89d4c1281e616533c16ba960bf1dfeee0f81432bb2fcf441e1a6b010303a1135":
        raise ValueError("Stage policy drift")
    rows = deepcopy(baseline)
    for before, row in zip(baseline, rows, strict=True):
        row.update(project(row, calendar), versao_contrato=VERSION)
        if any(row[k] != before[k] for k in before if k != "versao_contrato"):
            raise ValueError("Protected field changed")
        if set(row) - set(before) != set(FIELDS):
            raise ValueError("Unexpected fields")
    validate(rows)
    report = {"rows": len(rows), "before_fingerprint": before_hash, "after_fingerprint": fingerprint(rows),
              "classification": dict(Counter(r["classificacao_consumo"] for r in rows)),
              "metric_non_null": sum(r["sla_etapa_horas_uteis"] is not None for r in rows),
              "cloud_modified": False}
    with Path("runtime/validation/consumption_upgrade_20260923.json").open("x", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
