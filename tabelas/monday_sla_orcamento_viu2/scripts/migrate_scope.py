"""One-time, fixed-target scope migration. Default mode only reads production."""

import argparse
import base64
import gzip
import hashlib
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote

from publish_history import BUCKET, DATASET, PROJECT, GoogleAPI, gcloud, identity

TABLE = "monday_sla_orcamento_viu2"
SOURCE_SHA = "e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532"
POLICY = "escopo-sla-v3"
BASE = "https://bigquery.googleapis.com/bigquery/v2/projects/" + PROJECT
TABLE_URL = BASE + "/datasets/" + DATASET + "/tables/" + TABLE


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(rows, schema):
    normalized = []
    for row in rows:
        if set(row) != {f["name"] for f in schema}:
            raise ValueError("Campos divergentes")
        row = dict(row)
        for field in schema:
            key, kind = field["name"], field["type"]
            if row[key] is None:
                continue
            if kind == "TIMESTAMP":
                value = datetime.fromisoformat(row[key].replace("Z", "+00:00"))
                if value.utcoffset() is None:
                    raise ValueError("Timestamp sem fuso")
                row[key] = value.astimezone(UTC).isoformat(timespec="microseconds")
            elif kind == "DATETIME":
                row[key] = datetime.fromisoformat(row[key]).isoformat(timespec="microseconds")
            elif kind in ("FLOAT", "FLOAT64"):
                row[key] = float(row[key])
        normalized.append(row)
    normalized.sort(key=lambda r: r["interval_id"])
    return digest(json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode())


def payload(root):
    manifest = json.loads((root / "scope_manifest.json").read_bytes())
    if manifest["table"] != TABLE or manifest["policy"] != POLICY or manifest["source_sha"] != SOURCE_SHA:
        raise ValueError("Pacote de outro escopo")
    files = {}
    for name in ("original.ndjson.gz", "filtered.ndjson.gz", "schema.json"):
        files[name] = (root / name).read_bytes()
        if digest(files[name]) != manifest["files"][name]:
            raise ValueError("Checksum do pacote divergente")
    if digest(files["original.ndjson.gz"]) != SOURCE_SHA:
        raise ValueError("Historico original divergente")
    schema = json.loads(files["schema.json"])
    old, new = [[json.loads(line) for line in gzip.decompress(files[name]).splitlines()]
                for name in ("original.ndjson.gz", "filtered.ndjson.gz")]
    if len(old) != 17486 or len(new) != 14761:
        raise ValueError("Contagens fora do recorte aprovado")
    ids = {r["interval_id"] for r in new}
    items = {r["item_id"] for r in new}
    retained = [r for r in old if r["item_id"] in items]
    if len(ids) != len(new) or fingerprint(new, schema) != fingerprint(retained, schema):
        raise ValueError("O recorte alterou registros ou removeu somente parte de um projeto")
    return files, schema, old, new


def remote(api, schema):
    before = api.request(TABLE_URL)
    if before["schema"]["fields"] != schema or before.get("expirationTime"):
        raise ValueError("Schema ou expiracao remota inesperados")
    result = subprocess.check_output([
        "bq", "--project_id=" + PROJECT, "--format=json", "query", "--location=US",
        "--use_legacy_sql=false", "--use_cache=false", "--max_rows=100000",
        "--maximum_bytes_billed=104857600",
        "SELECT TO_JSON_STRING(t) AS registro FROM `" + PROJECT + "." + DATASET + "." + TABLE + "` AS t",
    ], text=True)
    rows = [json.loads(r["registro"]) for r in json.loads(result)]
    after = api.request(TABLE_URL)
    if before["etag"] != after["etag"] or len(rows) != int(after["numRows"]):
        raise ValueError("Tabela mudou durante a conferencia")
    return after, fingerprint(rows, schema)


def writers_stopped():
    for name in ("pipeline-monday-diario", "pipeline-orcamento-diario"):
        scheduler = json.loads(gcloud("scheduler", "jobs", "describe", name,
                                     "--project=" + PROJECT, "--location=us-central1", "--format=json"))
        if scheduler["state"] != "PAUSED":
            raise ValueError("Pause apenas as agendas do pipeline antes de aplicar")
    for name in ("pipeline-monday", "pipeline-orcamento"):
        executions = json.loads(gcloud("run", "jobs", "executions", "list", "--job=" + name,
                                      "--project=" + PROJECT, "--region=us-central1", "--limit=10000", "--format=json"))
        if any(not e.get("status", {}).get("completionTime") for e in executions):
            raise ValueError("Existe execucao do pipeline nao concluida")


def run(root, *, apply=False, expected_modified=None, payload_loader=None,
        writer_guard=None, policy=None, job_prefix="viu2_scope_v3_"):
    files, schema, old, new = (payload_loader or payload)(root)
    api = GoogleAPI()
    identity(api)
    if api.request(BASE + "/datasets/" + DATASET)["location"].upper() != "US":
        raise ValueError("Localizacao divergente")
    before, actual = remote(api, schema)
    target_hash = fingerprint(new, schema)
    receipt = {"table": PROJECT + "." + DATASET + "." + TABLE, "policy": policy or POLICY,
               "rows_before": int(before["numRows"]), "rows_after": len(new),
               "expected_modified": before["lastModifiedTime"], "kpi_approved": False}
    if actual == target_hash:
        return {**receipt, "status": "already_applied_content_verified"}
    if actual != fingerprint(old, schema):
        raise ValueError("Tabela difere da fonte original: nenhuma substituicao permitida")
    if not apply:
        return {**receipt, "status": "plan_verified_no_data_writes"}
    if not expected_modified or expected_modified != before["lastModifiedTime"]:
        raise ValueError("Plano desatualizado; execute plan novamente")
    (writer_guard or writers_stopped)()
    data = files["filtered.ndjson.gz"]
    sha = digest(data)
    name = "historico_viu2/sla_publicado/" + sha + "/review.ndjson.gz"
    uri = "gs://" + BUCKET + "/" + name
    gcloud("storage", "cp", "--no-clobber", str(root / "filtered.ndjson.gz"), uri)
    obj = api.request("https://storage.googleapis.com/storage/v1/b/" + BUCKET + "/o/" + quote(name, safe=""))
    if int(obj["size"]) != len(data) or obj["md5Hash"] != base64.b64encode(hashlib.md5(data).digest()).decode():
        raise ValueError("Artefato tratado GCS divergente")
    if api.request(TABLE_URL)["etag"] != before["etag"]:
        raise ValueError("Tabela mudou antes da carga")
    load = {"sourceUris": [uri], "sourceFormat": "NEWLINE_DELIMITED_JSON",
            "destinationTable": {"projectId": PROJECT, "datasetId": DATASET, "tableId": TABLE},
            "schema": {"fields": schema}, "writeDisposition": "WRITE_TRUNCATE",
            "createDisposition": "CREATE_NEVER", "maxBadRecords": 0}
    job_id = job_prefix + sha[:32]
    job_url = BASE + "/jobs/" + job_id + "?location=US"
    try:
        job = api.request(BASE + "/jobs", "POST", {
            "jobReference": {"projectId": PROJECT, "jobId": job_id, "location": "US"},
            "configuration": {"load": load}})
    except HTTPError as error:
        if error.code != 409:
            raise
        job = api.request(job_url)
    if any(job["configuration"]["load"].get(k) != v for k, v in load.items()):
        raise ValueError("Job existente com outra configuracao")
    deadline = time.monotonic() + 600
    while job["status"]["state"] != "DONE":
        if time.monotonic() >= deadline:
            raise RuntimeError("Resultado pendente; nao trocar job ID, repetir reconcilia")
        time.sleep(2)
        job = api.request(job_url)
    if job["status"].get("errorResult"):
        raise RuntimeError("Carga recusada; investigar antes de nova tentativa")
    after, actual = remote(api, schema)
    if actual != target_hash or int(after["numRows"]) != len(new):
        raise ValueError("Publicacao nao reconciliada")
    return {**receipt, "status": "applied_full_content_verified", "job_id": job_id, "source_sha": sha}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "apply"))
    parser.add_argument("--expected-modified")
    args = parser.parse_args()
    try:
        print(json.dumps(run(Path(__file__).resolve().parent, apply=args.mode == "apply",
                             expected_modified=args.expected_modified), indent=2))
    except Exception as error:
        print(json.dumps({"status": "migration_not_confirmed", "error_type": type(error).__name__}))
        if isinstance(error, (ValueError, RuntimeError)):
            print(str(error))
        raise SystemExit(1) from None
