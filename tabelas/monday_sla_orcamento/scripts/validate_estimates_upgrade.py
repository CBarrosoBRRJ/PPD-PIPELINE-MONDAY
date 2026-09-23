"""Pinned v5->v6 reconciliation: estimates are additive and official KPI unchanged."""

import json
from copy import deepcopy

from monday_sla_orcamento.consolidation import ESTIMATE_VERSION as VERSION
from monday_sla_orcamento.consolidation import TRAJECTORY_VERSION, validate
from monday_sla_orcamento.consumo import project as consumption_project
from monday_sla_orcamento.estimates import FIELDS, project
from monday_sla_orcamento.kpi_etapa import decision
from monday_sla_orcamento.publication import fingerprint
from monday_sla_orcamento.trajectory import project as trajectory_project
from sls_orcamento_ppd.rules.business_time import BusinessCalendar
from validate_trajectory_upgrade import checked

V5_FINGERPRINT = "b676c79b17237437c193bb28fde297ad9452b6ab34250a5bf9670c30ee53a895"


def candidate():
    base = [json.loads(line) for line in checked(
        "C:/Users/CCMB/Downloads/consolidado-publicado-v7.ndjson.gz",
        "e892c698bf6f5656f47b9beee3e3a0fdb7bb72904de4105d43c1a035eb5f0e6f").splitlines()]
    calendar = BusinessCalendar("America/Sao_Paulo")
    trajectory = trajectory_project(base)
    for row in base:
        eligible = decision(row, calendar)["elegivel_kpi_etapa_candidato"]
        row.update(versao_contrato=TRAJECTORY_VERSION, elegivel_comparacao=eligible,
                   validacao_negocio="aprovado_etapa_origem_v1" if eligible else "nao_elegivel_etapa_origem_v1")
        row.update(consumption_project(row, calendar), **trajectory[row["interval_id"]])
    if fingerprint(base) != V5_FINGERPRINT:
        raise ValueError("Base v5 divergiu")
    rows = deepcopy(base)
    estimates = project(rows, calendar)
    for before, row in zip(base, rows, strict=True):
        row.update(estimates[row["interval_id"]], versao_contrato=VERSION)
        if any(before[k] != row[k] for k in before if k != "versao_contrato"):
            raise ValueError("Campo protegido alterado")
        if set(row) - set(before) != set(FIELDS):
            raise ValueError("Campos inesperados")
    validate(rows)
    return rows


def main():
    rows = candidate()
    print(json.dumps({
        "before_fingerprint": V5_FINGERPRINT, "after_fingerprint": fingerprint(rows),
        "rows": len(rows), "projects": len({r["projeto_id"] for r in rows}),
        "estimated_rows": sum(r["saida_estimada_utc"] is not None for r in rows),
        "official_kpi_rows": sum(r["sla_etapa_horas_uteis"] is not None for r in rows),
        "protected_fields_changed": 0, "cloud_modified": False,
        "example": [{k: r[k] for k in FIELDS} for r in rows
                    if r["projeto_id"] == "ef79e6b0-cb2d-55ef-946c-143119e68420"
                    and r["saida_estimada_utc"] is not None],
    }, indent=2))


if __name__ == "__main__":
    main()
