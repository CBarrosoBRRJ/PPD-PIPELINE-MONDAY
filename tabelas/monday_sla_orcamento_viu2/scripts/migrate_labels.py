"""Coordinated historical-label migration. Explicit apply; no scheduler/IAM changes."""

import argparse
import base64
import hashlib
import json
import tempfile
from pathlib import Path
from urllib.parse import quote

import migrate_scope as loader
from plan_label_migration import load_package
from publish_history import BUCKET, PROJECT, GoogleAPI, gcloud, identity

OLD_SHA = "e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532"
NEW_SHA = "d0aab3fdb25cb1f3746ee0f1c6db37c419e255034b6ce9786ff3e6d84e78af1e"
TARGET_SHA = "0a8016b8dd633fb1e94bc5b7f27c38f3b485174b3f1f76eaa8fa4481c6cf5cea"
CONTROL = "gs://" + BUCKET + "/consolidado/diario/control.json"
OLD_IDENTITY = {"format": 1, "table": PROJECT + ".viu_agenciamento.monday_sla_orcamento",
                "location": "US", "scope_policy": "escopo-sla-v3",
                "contract": "sla-consolidado-evidencias-v2", "history_sha": OLD_SHA,
                "map_sha": "486845629229aaa881c38ab87d58cec49811f539642d413d9aa29f07569399eb"}
NEW_IDENTITY = {**OLD_IDENTITY, "history_sha": NEW_SHA}


def payload(root):
    schema, old, new = load_package(root)
    blob = (root / "after.ndjson.gz").read_bytes()
    if hashlib.sha256(blob).hexdigest() != TARGET_SHA:
        raise ValueError("Candidata incorreta")
    # Loader uses this exact local filename for upload.
    if (root / "filtered.ndjson.gz").read_bytes() != blob:
        raise ValueError("Artefato de carga divergente")
    return {"filtered.ndjson.gz": blob}, schema, old, new


def control():
    args = ("storage", "objects", "describe", CONTROL, "--format=json")
    before = json.loads(gcloud(*args))
    value = json.loads(gcloud("storage", "cat", CONTROL))
    after = json.loads(gcloud(*args))
    if str(before["generation"]) != str(after["generation"]):
        raise ValueError("Controle mudou durante leitura")
    if value.get("pending") is not None:
        raise ValueError("Consolidada possui publicacao pendente")
    if value.get("identity") not in (OLD_IDENTITY, NEW_IDENTITY):
        raise ValueError("Identidade do controle inesperada")
    return value, str(after["generation"])


def stopped(expected_image):
    if not expected_image or "@sha256:" not in expected_image:
        raise ValueError("Informe imagem v7 por digest")
    schedule = json.loads(gcloud("scheduler", "jobs", "describe", "pipeline-monday-diario",
                                 "--project=" + PROJECT, "--location=us-central1", "--format=json"))
    if schedule["state"] != "PAUSED":
        raise ValueError("Agenda pipeline-monday-diario deve estar pausada")
    job = json.loads(gcloud("run", "jobs", "describe", "pipeline-monday", "--project=" + PROJECT,
                            "--region=us-central1", "--format=json"))
    containers = job["spec"]["template"]["spec"]["template"]["spec"]["containers"]
    if (len(containers) != 1 or containers[0].get("image") != expected_image
            or containers[0].get("command") != ["pipeline-monday"]
            or containers[0].get("args") != ["plan", "--manifest", "/app/pipelines.json"]):
        raise ValueError("Job precisa estar na imagem aprovada e modo plan")
    runs = json.loads(gcloud("run", "jobs", "executions", "list", "--job=pipeline-monday",
                             "--project=" + PROJECT, "--region=us-central1", "--limit=10000", "--format=json"))
    if any(not r.get("status", {}).get("completionTime") for r in runs):
        raise ValueError("Execucao nao concluida")


def upload_source(root, api):
    path = root / "coordinator_source.ndjson.gz"
    blob = path.read_bytes()
    if hashlib.sha256(blob).hexdigest() != NEW_SHA:
        raise ValueError("Fonte do coordenador divergente")
    name = "historico_viu2/sla_publicado/" + NEW_SHA + "/review.ndjson.gz"
    gcloud("storage", "cp", "--no-clobber", str(path), "gs://" + BUCKET + "/" + name)
    metadata = api.request("https://storage.googleapis.com/storage/v1/b/" + BUCKET + "/o/" + quote(name, safe=""))
    if (int(metadata["size"]) != len(blob)
            or metadata["md5Hash"] != base64.b64encode(hashlib.md5(blob).digest()).decode()):
        raise ValueError("Fonte GCS nao reconciliada")


def run(root, *, apply=False, expected_modified=None, expected_generation=None, expected_image=None):
    payload(root)
    value, generation = control()
    if not apply:
        receipt = loader.run(root, payload_loader=payload, policy="historical-labels-v2")
        return {**receipt, "control_generation": generation, "control_identity": value["identity"]}
    stopped(expected_image)
    already_migrated = value["identity"] == NEW_IDENTITY
    if not already_migrated and str(expected_generation) != generation:
        raise ValueError("Geracao do plano desatualizada")
    api = GoogleAPI()
    identity(api)
    upload_source(root, api)
    receipt = loader.run(root, apply=True, expected_modified=expected_modified,
                         payload_loader=payload, writer_guard=lambda: stopped(expected_image),
                         policy="historical-labels-v2", job_prefix="viu2_labels_v2_")
    stopped(expected_image)
    current, current_generation = control()
    if already_migrated:
        if current["identity"] != NEW_IDENTITY:
            raise ValueError("Controle alterado apos conferencia")
        return {**receipt, "control_status": "already_migrated", "daily_rebuild_required": True}
    if current_generation != generation or current != value:
        raise ValueError("Historico verificado, mas controle mudou: manter agenda pausada")
    updated = {**value, "identity": NEW_IDENTITY}
    # The active descriptor remains the existing consolidated publication until
    # v7 rebuilds it. Never pretend a new consolidated publication already exists.
    with tempfile.TemporaryDirectory(prefix="monday-label-control-") as directory:
        file = Path(directory) / "control.json"
        file.write_text(json.dumps(updated), encoding="utf-8")
        gcloud("storage", "cp", "--if-generation-match=" + generation,
               "--content-type=application/json", str(file), CONTROL)
    actual, new_generation = control()
    if actual != updated:
        raise ValueError("Controle nao reconciliado")
    return {**receipt, "control_status": "history_reference_migrated",
            "control_generation": new_generation, "daily_rebuild_required": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "apply"))
    parser.add_argument("--expected-modified")
    parser.add_argument("--expected-generation")
    parser.add_argument("--expected-image")
    args = parser.parse_args()
    try:
        print(json.dumps(run(Path(__file__).resolve().parent, apply=args.mode == "apply",
                             expected_modified=args.expected_modified, expected_generation=args.expected_generation,
                             expected_image=args.expected_image), indent=2))
    except Exception as error:
        print(json.dumps({"status": "migration_not_confirmed", "error_type": type(error).__name__}))
        if isinstance(error, (ValueError, RuntimeError)):
            print(str(error))
        raise SystemExit(1) from None
