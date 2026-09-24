"""Pinned v7 -> v8 control migration. Requires reviewed current plan, no table writes."""

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import migrate_kpi_contract as base

OLD = {**base.OLD, "contract": "sla-consolidado-analise-v7"}
NEW = {**OLD, "contract": "sla-consolidado-precificacao-v8"}


def read():
    before = json.loads(base.cli("storage", "objects", "describe", base.CONTROL, "--format=json"))
    control = json.loads(base.cli("storage", "cat", base.CONTROL))
    after = json.loads(base.cli("storage", "objects", "describe", base.CONTROL, "--format=json"))
    if before["generation"] != after["generation"]:
        raise ValueError("Controle mudou durante leitura")
    if control.get("pending") is not None or control.get("identity") not in (OLD, NEW):
        raise ValueError("Identidade ou publicacao pendente impede migracao")
    active = control.get("active") or {}
    if (not re.fullmatch(r"[0-9a-f]{64}", active.get("fingerprint", ""))
            or type(active.get("rows")) is not int or active["rows"] <= 0):
        raise ValueError("Publicacao ativa invalida")
    return control, str(after["generation"])


def run(*, apply=False, generation=None, fingerprint=None, image=None):
    control, observed_generation = read()
    if not apply:
        return {"status": "plan_no_writes", "generation": observed_generation,
                "identity": control["identity"], "fingerprint": control["active"]["fingerprint"],
                "rows": control["active"]["rows"], "target_contract": NEW["contract"]}
    if not image or not re.fullmatch(r".+@sha256:[0-9a-f]{64}", image):
        raise ValueError("Informe digest completo da imagem validada")
    base.stopped(image)
    if observed_generation != generation or control["active"]["fingerprint"] != fingerprint:
        raise ValueError("Plano desatualizado; repetir leitura e revisao")
    if control["identity"] == NEW:
        return {"status": "already_migrated", "daily_rebuild_required": True}
    again, current_generation = read()
    if again != control or current_generation != observed_generation:
        raise ValueError("Controle mudou; manter agenda pausada")
    updated = {**control, "identity": NEW}
    with tempfile.TemporaryDirectory(prefix="monday-pricing-contract-") as directory:
        path = Path(directory) / "control.json"
        path.write_text(json.dumps(updated), encoding="utf-8")
        base.cli("storage", "cp", "--if-generation-match=" + observed_generation,
                 "--content-type=application/json", str(path), base.CONTROL)
    confirmed, new_generation = read()
    if confirmed != updated:
        raise ValueError("Migracao nao reconciliada")
    return {"status": "contract_migrated", "generation": new_generation,
            "tables_modified": False, "daily_rebuild_required": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "apply"))
    parser.add_argument("--expected-generation")
    parser.add_argument("--expected-fingerprint")
    parser.add_argument("--expected-image")
    args = parser.parse_args()
    try:
        print(json.dumps(run(apply=args.mode == "apply", generation=args.expected_generation,
                             fingerprint=args.expected_fingerprint, image=args.expected_image), indent=2))
    except (ValueError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "migration_not_confirmed", "error_type": type(error).__name__}))
        if isinstance(error, ValueError):
            print(str(error))
        raise SystemExit(1) from None
