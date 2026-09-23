"""Reconcile additive v5 against pinned v4; no writes to source or cloud."""

import gzip
import hashlib
import json
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from monday_sla_orcamento.consolidation import CONSUMPTION_VERSION, validate
from monday_sla_orcamento.consolidation import TRAJECTORY_VERSION as VERSION
from monday_sla_orcamento.consumo import project as consumption_project
from monday_sla_orcamento.kpi_etapa import decision
from monday_sla_orcamento.publication import fingerprint
from monday_sla_orcamento.trajectory import FIELDS, audit, project
from sls_orcamento_ppd.rules.business_time import BusinessCalendar

V4_FINGERPRINT = "3c3ee3cb5a92a96052687300f45efd287ff440f0620d169db4fd64aa961e8f78"


def checked(path, sha):
    content = Path(path).read_bytes()
    if hashlib.sha256(content).hexdigest() != sha:
        raise ValueError("Fonte local: checksum divergente")
    return gzip.decompress(content)


def main():
    base = [json.loads(line) for line in checked(
        "C:/Users/CCMB/Downloads/consolidado-publicado-v7.ndjson.gz",
        "e892c698bf6f5656f47b9beee3e3a0fdb7bb72904de4105d43c1a035eb5f0e6f").splitlines()]
    calendar = BusinessCalendar("America/Sao_Paulo")
    for row in base:
        eligible = decision(row, calendar)["elegivel_kpi_etapa_candidato"]
        row.update(versao_contrato=CONSUMPTION_VERSION, elegivel_comparacao=eligible,
                   validacao_negocio="aprovado_etapa_origem_v1" if eligible else "nao_elegivel_etapa_origem_v1")
        row.update(consumption_project(row, calendar))
    if fingerprint(base) != V4_FINGERPRINT:
        raise ValueError("Base v4 divergiu; nao publicar")
    rows = deepcopy(base)
    additions = project(rows)
    for before, row in zip(base, rows, strict=True):
        row.update(additions[row["interval_id"]], versao_contrato=VERSION)
        if any(before[k] != row[k] for k in before if k != "versao_contrato"):
            raise ValueError("Campo protegido alterado")
        if set(row) - set(before) != set(FIELDS):
            raise ValueError("Schema aditivo divergente")
    validate(rows)
    groups = defaultdict(list)
    for row in rows:
        groups[row["projeto_id"]].append(row)
    singles = [group[0] for group in groups.values() if len(group) == 1]
    state = json.loads(checked("C:/Users/CCMB/Downloads/state.json.gz",
                              "3889bde42e846f7ef3768df4e4d88d0cfe575d0997ac29306cdf13b77703bfe0"))
    item_ids = {int(r["item_id_globocorp"]) for r in singles}
    raw_matches = [r for r in state["bronze_monday_activity_log_raw"] if int(r["item_id"]) in item_ids]
    report = audit(rows)
    report.pop("details")
    report.update(before_fingerprint=V4_FINGERPRINT, after_fingerprint=fingerprint(rows),
                  kpi_rows=sum(r["sla_etapa_horas_uteis"] is not None for r in rows),
                  project_quality=dict(Counter(r["qualidade_trajetoria"] for r in rows
                                               if r["eh_ultima_etapa_observada"])),
                  singleton_globocorp_events_in_downloaded_state=len(raw_matches),
                  protected_fields_changed=0, cloud_modified=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
