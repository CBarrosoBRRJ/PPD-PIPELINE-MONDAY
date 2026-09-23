"""Explicit control-only v2->v3 migration. Standard library, no table writes."""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

PROJECT = "gglobo-viu-dados-hdg-prd"
CONTROL = "gs://" + PROJECT + "-ppd-pipeline-monday/consolidado/diario/control.json"
OLD = {"format": 1, "table": PROJECT + ".viu_agenciamento.monday_sla_orcamento",
       "location": "US", "scope_policy": "escopo-sla-v3", "contract": "sla-consolidado-evidencias-v2",
       "history_sha": "d0aab3fdb25cb1f3746ee0f1c6db37c419e255034b6ce9786ff3e6d84e78af1e",
       "map_sha": "486845629229aaa881c38ab87d58cec49811f539642d413d9aa29f07569399eb"}
NEW = {**OLD, "contract": "sla-consolidado-etapa-v3"}
FINGERPRINT = "6c33244f4fff85a9f5ebd0e09685aed8a6bf746eb0f5d8df92e7b91363447987"


def cli(*args):
    return subprocess.check_output(["gcloud", *args, "--project=" + PROJECT], text=True)


def read_control():
    before = json.loads(cli("storage", "objects", "describe", CONTROL, "--format=json"))
    control = json.loads(cli("storage", "cat", CONTROL))
    after = json.loads(cli("storage", "objects", "describe", CONTROL, "--format=json"))
    if before["generation"] != after["generation"]:
        raise ValueError("Controle mudou durante leitura")
    if control.get("pending") is not None or control.get("identity") not in (OLD, NEW):
        raise ValueError("Controle pendente ou identidade inesperada")
    if control["identity"] == OLD and (
        control.get("active", {}).get("fingerprint") != FINGERPRINT
        or control["active"].get("rows") != 9648
    ):
        raise ValueError("Publicacao mudou: conferir nova base antes da migracao")
    return control, str(after["generation"])


def stopped(image):
    if not image or not image.startswith(
        "us-central1-docker.pkg.dev/" + PROJECT + "/viu-pipelines/pipeline-monday@sha256:"
    ):
        raise ValueError("Informe digest da imagem aprovada")
    agenda = json.loads(cli("scheduler", "jobs", "describe", "pipeline-monday-diario",
                           "--location=us-central1", "--format=json"))
    if agenda["state"] != "PAUSED":
        raise ValueError("Pause apenas pipeline-monday-diario")
    job = json.loads(cli("run", "jobs", "describe", "pipeline-monday",
                        "--region=us-central1", "--format=json"))
    containers = job["spec"]["template"]["spec"]["template"]["spec"]["containers"]
    if len(containers) != 1 or any(containers[0].get(k) != v for k, v in {
        "image": image, "command": ["pipeline-monday"], "args": ["plan", "--manifest", "/app/pipelines.json"]
    }.items()):
        raise ValueError("Job deve estar na imagem aprovada em modo plan")
    runs = json.loads(cli("run", "jobs", "executions", "list", "--job=pipeline-monday",
                         "--region=us-central1", "--limit=10000", "--format=json"))
    if any(not r.get("status", {}).get("completionTime") for r in runs):
        raise ValueError("Existe execucao nao concluida")


def run(*, apply=False, expected_generation=None, image=None):
    control, generation = read_control()
    if not apply:
        return {"status": "plan_no_writes", "generation": generation,
                "identity": control["identity"], "fingerprint": control["active"]["fingerprint"]}
    stopped(image)
    if control["identity"] == NEW:
        return {"status": "already_migrated", "daily_rebuild_required": True}
    if generation != expected_generation:
        raise ValueError("Geracao desatualizada; nao forcar")
    current, current_generation = read_control()
    if current != control or current_generation != generation:
        raise ValueError("Controle mudou; manter agenda pausada")
    updated = {**control, "identity": NEW}
    with tempfile.TemporaryDirectory(prefix="monday-kpi-contract-") as directory:
        path = Path(directory) / "control.json"
        path.write_text(json.dumps(updated), encoding="utf-8")
        cli("storage", "cp", "--if-generation-match=" + generation,
            "--content-type=application/json", str(path), CONTROL)
    confirmed, new_generation = read_control()
    if confirmed != updated:
        raise ValueError("Migracao nao reconciliada")
    return {"status": "contract_migrated", "generation": new_generation,
            "tables_modified": False, "daily_rebuild_required": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "apply"))
    parser.add_argument("--expected-generation")
    parser.add_argument("--expected-image")
    args = parser.parse_args()
    try:
        print(json.dumps(run(apply=args.mode == "apply", expected_generation=args.expected_generation,
                             image=args.expected_image), indent=2))
    except (ValueError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "migration_not_confirmed", "error_type": type(error).__name__}))
        if isinstance(error, ValueError):
            print(str(error))
        raise SystemExit(1) from None
