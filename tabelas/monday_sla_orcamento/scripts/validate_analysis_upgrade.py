"""Offline v6->v7 reconciliation; observed KPI and estimates remain unchanged."""

import json
from collections import Counter
from copy import deepcopy

from monday_sla_orcamento.analysis_duration import FIELDS, project
from monday_sla_orcamento.consolidation import VERSION, validate
from monday_sla_orcamento.publication import fingerprint
from validate_estimates_upgrade import candidate

V6_FINGERPRINT = "daba7914c4ccbcf8f6d7d60c1b97e2bce742a62a86b379690a89b48cca069bef"


def main():
    before = candidate()
    if fingerprint(before) != V6_FINGERPRINT:
        raise ValueError("Base v6 divergiu")
    rows = deepcopy(before)
    for old, row in zip(before, rows, strict=True):
        row.update(project(row), versao_contrato=VERSION)
        if any(old[k] != row[k] for k in old if k != "versao_contrato"):
            raise ValueError("Campo protegido alterado")
        if set(row) - set(old) != set(FIELDS):
            raise ValueError("Schema aditivo divergente")
    validate(rows)
    print(json.dumps({"before_fingerprint": V6_FINGERPRINT, "after_fingerprint": fingerprint(rows),
                      "rows": len(rows), "projects": len({r["projeto_id"] for r in rows}),
                      "origins": dict(Counter(r["origem_duracao_analise"] for r in rows)),
                      "unified_values": sum(r["duracao_analise_horas_uteis"] is not None for r in rows),
                      "official_kpi_values": sum(r["sla_etapa_horas_uteis"] is not None for r in rows),
                      "protected_fields_changed": 0, "cloud_modified": False}, indent=2))


if __name__ == "__main__":
    main()
