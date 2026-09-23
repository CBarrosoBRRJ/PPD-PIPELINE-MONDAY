"""Verify v3 eligibility on the exact downloaded v7 artifact; no cloud mutation."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

from audit_kpi_candidate import checked
from monday_sla_orcamento.consolidation import STAGE_VERSION, validate
from monday_sla_orcamento.kpi_etapa import decision
from monday_sla_orcamento.publication import fingerprint
from reconcile_kpi_snapshot import PUBLISHED_FINGERPRINT, PUBLISHED_SHA
from sls_orcamento_ppd.rules.business_time import BusinessCalendar


def main():
    original = [json.loads(line) for line in checked(
        "C:/Users/CCMB/Downloads/consolidado-publicado-v7.ndjson.gz", PUBLISHED_SHA).splitlines()]
    if fingerprint(original) != PUBLISHED_FINGERPRINT:
        raise ValueError("Unexpected published snapshot")
    upgraded = deepcopy(original)
    calendar = BusinessCalendar("America/Sao_Paulo")
    for row in upgraded:
        eligible = decision(row, calendar)["elegivel_kpi_etapa_candidato"]
        row.update(versao_contrato=STAGE_VERSION, elegivel_comparacao=eligible,
                   validacao_negocio="aprovado_etapa_origem_v1" if eligible else "nao_elegivel_etapa_origem_v1")
    validate(upgraded)
    changed = Counter()
    for before, after in zip(original, upgraded, strict=True):
        fields = {key for key in before if before[key] != after[key]}
        if fields - {"versao_contrato", "elegivel_comparacao", "validacao_negocio"}:
            raise ValueError("Protected field changed")
        changed.update(fields)
    result = {"rows": len(upgraded), "before_fingerprint": PUBLISHED_FINGERPRINT,
              "after_fingerprint": fingerprint(upgraded), "changed_fields": dict(changed),
              "eligible_by_origin": dict(Counter(r["ambiente_origem"] for r in upgraded if r["elegivel_comparacao"])),
              "cloud_modified": False, "deployment_verified": False}
    with Path("runtime/validation/kpi_upgrade_validation_20260923.json").open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
