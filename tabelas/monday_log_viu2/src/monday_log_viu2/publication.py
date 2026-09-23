"""Publish a verified rescue once. Runs locally or in Cloud Shell using gcloud."""

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

PROJECT = "gglobo-viu-dados-hdg-prd"
PROJECT_NUMBER = "241421786646"
ACCOUNT = "caio.barroso@viu.com.br"
DATASET = "viu_agenciamento"
TABLE = "log_monday_viu2"
BUCKET = PROJECT + "-ppd-pipeline-monday"


def sha(content):
    return hashlib.sha256(content).hexdigest()


def gcloud(*args, capture=True):
    executable = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if not executable:
        raise RuntimeError("Instale gcloud ou use Cloud Shell")
    result = subprocess.run(
        [executable, *args, "--account=" + ACCOUNT], capture_output=True,
        text=True, encoding="utf-8", check=False,
    )
    if result.returncode:
        raise RuntimeError("Comando gcloud falhou; verifique login/permissoes corporativas")
    if capture:
        return result.stdout.strip()
    return None


def identity(api):
    claims = api.request("https://www.googleapis.com/oauth2/v3/userinfo")
    if claims.get("email") != ACCOUNT:
        raise RuntimeError("Credencial do terminal nao corresponde a conta corporativa")


class GoogleAPI:
    def __init__(self):
        self.token = gcloud("auth", "print-access-token")

    def request(self, url, method="GET", body=None):
        data = json.dumps(body).encode() if body is not None else None
        request = Request(url, data=data, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
        })
        with urlopen(request, timeout=90) as response:
            return json.load(response)


def local_files(archive):
    manifest = json.loads((archive / "manifest.json").read_bytes())
    export = json.loads((archive / "structured/export_manifest.json").read_bytes())
    if manifest["status"] != "complete_available_api_history":
        raise RuntimeError("Arquivo incompleto")
    if (manifest["source"], str(manifest["account_id"]), str(manifest["board_id"])) != (
        "viu2", "5890468", "18393336134"
    ):
        raise RuntimeError("Arquivo nao pertence ao quadro viu2 autorizado")
    if export["source_manifest_sha256"] != sha((archive / "manifest.json").read_bytes()):
        raise RuntimeError("Manifesto alterado")
    if export["rows"] != manifest["unique_events"]:
        raise RuntimeError("Contagens divergentes")
    for name, record in manifest["files"].items():
        if sha((archive / name).read_bytes()) != record["sha256"]:
            raise RuntimeError("Arquivo bruto corrompido")
    context = json.loads((archive / "context/context_manifest.json").read_bytes())
    if context["status"] != "complete_current_item_context":
        raise RuntimeError("Contexto incompleto")
    for name, record in context["files"].items():
        if sha((archive / "context" / name).read_bytes()) != record["sha256"]:
            raise RuntimeError("Contexto corrompido")
    if sha((archive / "structured" / export["file"]).read_bytes()) != export["sha256"]:
        raise RuntimeError("Exportacao corrompida")
    files = {}
    for path in archive.rglob("*"):
        if path.is_file():
            content = path.read_bytes()
            files[path.relative_to(archive).as_posix()] = {
                "size": len(content),
                "md5": base64.b64encode(hashlib.md5(content).digest()).decode(),
            }
    return files, export


def publish(archive):
    files, export = local_files(archive)
    print(f"Arquivos locais validados: {len(files)}; linhas: {export['rows']}", flush=True)
    api = GoogleAPI()
    identity(api)
    bq = "https://bigquery.googleapis.com/bigquery/v2/projects/" + PROJECT
    dataset = api.request(bq + "/datasets/" + DATASET)
    location = dataset["location"]
    bucket_url = "https://storage.googleapis.com/storage/v1/b/" + BUCKET
    try:
        bucket = api.request(bucket_url)
    except HTTPError as error:
        if error.code != 404:
            raise
        bucket = api.request(
            "https://storage.googleapis.com/storage/v1/b?" + urlencode({"project": PROJECT}),
            "POST", {"name": BUCKET, "location": location,
                     "iamConfiguration": {"uniformBucketLevelAccess": {"enabled": True},
                                          "publicAccessPrevention": "enforced"},
                     "versioning": {"enabled": True}},
        )
        print("Bucket privado dedicado criado.", flush=True)
    if str(bucket["projectNumber"]) != PROJECT_NUMBER:
        raise RuntimeError("Bucket pertence a outro projeto")
    if bucket.get("iamConfiguration", {}).get("publicAccessPrevention") != "enforced":
        raise RuntimeError("Bucket existente exige revisao de acesso publico")
    if bucket.get("lifecycle", {}).get("rule"):
        raise RuntimeError("Bucket existente tem lifecycle; revisar antes de arquivar")
    if not bucket.get("versioning", {}).get("enabled"):
        raise RuntimeError("Bucket existente sem versionamento; revisar")
    prefix = "historico_viu2/" + archive.name + "/"
    gcloud("storage", "cp", "--recursive", "--no-clobber", str(archive),
           "gs://" + BUCKET + "/historico_viu2/", capture=False)
    remote = {}
    page = None
    while True:
        params = {"prefix": prefix, "maxResults": 1000}
        if page:
            params["pageToken"] = page
        data = api.request(bucket_url + "/o?" + urlencode(params))
        remote.update({v["name"][len(prefix):]: v for v in data.get("items", [])})
        page = data.get("nextPageToken")
        if not page:
            break
    for name, expected in files.items():
        actual = remote.get(name, {})
        if int(actual.get("size", -1)) != expected["size"] or actual.get("md5Hash") != expected["md5"]:
            raise RuntimeError("Copia GCS nao reconciliada; carga BQ bloqueada")
    print(f"GCS verificado: {len(files)} objetos.", flush=True)
    uri = "gs://" + BUCKET + "/" + prefix + "structured/" + export["file"]
    schema = json.loads((archive / "structured/schema.json").read_bytes())
    job_id = "resgate_viu2_" + export["sha256"][:32]
    load = {"sourceUris": [uri], "sourceFormat": "NEWLINE_DELIMITED_JSON",
            "destinationTable": {"projectId": PROJECT, "datasetId": DATASET, "tableId": TABLE},
            "schema": {"fields": schema}, "writeDisposition": "WRITE_EMPTY",
            "createDisposition": "CREATE_IF_NEEDED", "maxBadRecords": 0}
    job_url = bq + "/jobs/" + job_id + "?" + urlencode({"location": location})
    try:
        job = api.request(bq + "/jobs", "POST", {
            "jobReference": {"projectId": PROJECT, "jobId": job_id, "location": location},
            "configuration": {"load": load},
        })
    except HTTPError as error:
        if error.code != 409:
            raise
        job = api.request(job_url)
    actual_load = job["configuration"]["load"]
    for key in ("sourceUris", "destinationTable", "writeDisposition", "schema"):
        if actual_load.get(key) != load[key]:
            raise RuntimeError("Job existente nao corresponde a carga solicitada")
    deadline = time.monotonic() + 900
    while job["status"]["state"] != "DONE":
        if time.monotonic() > deadline:
            raise RuntimeError("Job ainda em execucao; reexecute para reconciliar mesmo ID")
        time.sleep(2)
        job = api.request(job_url)
    if job["status"].get("errorResult"):
        raise RuntimeError("Job BQ falhou; tabela existente nao foi sobrescrita")
    if int(job["statistics"]["load"]["outputRows"]) != export["rows"]:
        raise RuntimeError("Quantidade carregada divergente")
    table_url = bq + "/datasets/" + DATASET + "/tables/" + quote(TABLE)
    table = api.request(table_url)
    if int(table["numRows"]) != export["rows"] or table["schema"]["fields"] != schema:
        raise RuntimeError("Tabela BQ nao reconciliada")
    if table.get("expirationTime"):
        api.request(table_url, "PATCH", {"expirationTime": None})
        if api.request(table_url).get("expirationTime"):
            raise RuntimeError("Expiracao da tabela nao removida")
    receipt = {"status": "published_and_verified", "rows": export["rows"],
               "table": PROJECT + "." + DATASET + "." + TABLE,
               "bucket": BUCKET, "prefix": prefix, "job_id": job_id,
               "location": location, "objects_verified": len(files),
               "export_sha256": export["sha256"],
               "structured_object_generation": remote["structured/" + export["file"]]["generation"]}
    Path("publish_receipt_viu2.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    args = parser.parse_args()
    try:
        publish(args.archive.resolve())
    except HTTPError as exc:
        print(f"GCP recusou a operacao: HTTP {exc.code}. Verifique IAM da conta corporativa.")
        raise SystemExit(1) from None
    except (RuntimeError, OSError, KeyError, ValueError) as exc:
        print(f"Publicacao interrompida: {type(exc).__name__}. Nenhuma SLA foi sobrescrita.")
        if isinstance(exc, RuntimeError):
            print(str(exc))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
