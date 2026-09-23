"""Offline label-rebuild reconciliation. No network or publication."""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

from historico_viu2.eligibility import frozen_inputs
from historico_viu2.review_contract import validate
from monday_comum.escopo_sla import filtrar_projetos, motivos_input, normalizar_titulo


def read_rows(path):
    return [json.loads(line) for line in gzip.decompress(path.read_bytes()).splitlines()]


def reconcile(before, after):
    validate(after)
    old = {r["interval_id"]: r for r in before}
    new = {r["interval_id"]: r for r in after}
    if len(old) != len(before) or len(new) != len(after) or old.keys() != new.keys():
        raise ValueError("Reconstrucao alterou conjunto de chaves")
    allowed = {"status_nome", "qualidade_rotulo", "pendencias_json"}
    changed = Counter()
    recovered = []
    for key, row in new.items():
        fields = {field for field in row if row[field] != old[key][field]}
        if fields - allowed:
            raise ValueError("Reconstrucao alterou campo protegido")
        changed.update(fields)
        if row["status_nome"] != old[key]["status_nome"]:
            if old[key]["status_nome"] is not None or not row["status_nome"]:
                raise ValueError("Rotulo previamente observado alterado")
            if row["qualidade_rotulo"] != "label_observed_at_exit_previous_value":
                raise ValueError("Recuperacao sem qualidade explicita")
            recovered.append(row)
    return {"rows": len(after), "keys_dates_durations_scope_preserved": True,
            "changed_fields": dict(changed), "recovered_labels": len(recovered),
            "recovered_by_index": dict(Counter(r["status_index"] for r in recovered)),
            "unknown_labels_remaining": sum(r["status_nome"] is None for r in after),
            "kpi_approved": False, "cloud_modified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    inputs = frozen_inputs(lambda name: (args.archive / name).read_bytes())
    before = filtrar_projetos(read_rows(args.before), inputs)
    after = read_rows(args.after)
    result = reconcile(before, after)
    if filtrar_projetos(after, inputs) != after:
        raise ValueError("Candidata contem projeto fora do escopo comprovado")
    projects = {(r["board_id"], r["item_id"]) for r in after}
    result["input_audit"] = {
        "source": "checksum_verified_frozen_viu2_context",
        "projects": len(projects),
        "missing_context": sum(key not in inputs for key in projects),
        "denied_input": sum(bool(motivos_input(inputs[key])) for key in projects),
        "verified_blank_allowed": sum(not normalizar_titulo(inputs[key]) for key in projects),
    }
    result["sources_sha256"] = {
        "before": hashlib.sha256(args.before.read_bytes()).hexdigest(),
        "after": hashlib.sha256(args.after.read_bytes()).hexdigest(),
    }
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
