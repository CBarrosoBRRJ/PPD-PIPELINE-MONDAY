"""User-authorized final historical table name, with pending business validation.

This is not the consolidated table and never changes the daily pipeline.
"""

import base64
import gzip
import hashlib
import json
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote

try:  # Standalone ZIP keeps its helper beside this script.
    from publish_history import BUCKET, DATASET, PROJECT, GoogleAPI, gcloud, identity
except ModuleNotFoundError:
    from monday_log_viu2.publication import BUCKET, DATASET, PROJECT, GoogleAPI, gcloud, identity

TABLE = "monday_sla_orcamento_viu2"
DATA_SHA = "e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532"
SCHEMA_SHA = "89da8ddf01e90f1ac5d7da28f262fd978250d805c6b1881aea126a2b24eea7cf"


def local_payload(root):
    data = (root / "review.ndjson.gz").read_bytes()
    schema_raw = (root / "schema.json").read_bytes()
    if hashlib.sha256(data).hexdigest() != DATA_SHA or hashlib.sha256(schema_raw).hexdigest() != SCHEMA_SHA:
        raise ValueError("Pacote divergente; nenhuma carga autorizada")
    rows = [json.loads(line) for line in gzip.decompress(data).splitlines()]
    if len(rows) != 17486 or len({r["interval_id"] for r in rows}) != len(rows):
        raise ValueError("Quantidade/chaves divergentes")
    if any(r["elegivel_comparacao"] is not False or r["validacao_negocio"] != "pendente" for r in rows):
        raise ValueError("Previa nao pode conter aprovacao de KPI")
    return data, json.loads(schema_raw)


def publish(root):
    data, schema = local_payload(root)
    api = GoogleAPI()
    identity(api)
    base = "https://bigquery.googleapis.com/bigquery/v2/projects/" + PROJECT
    if api.request(base + "/datasets/" + DATASET)["location"].upper() != "US":
        raise ValueError("Localizacao inesperada")
    object_name = "historico_viu2/sla_publicado/" + DATA_SHA + "/review.ndjson.gz"
    uri = "gs://" + BUCKET + "/" + object_name
    gcloud("storage", "cp", "--no-clobber", str(root / "review.ndjson.gz"), uri, capture=False)
    remote = api.request("https://storage.googleapis.com/storage/v1/b/" + BUCKET + "/o/" + quote(object_name, safe=""))
    if (int(remote["size"]) != len(data) or remote["md5Hash"] !=
            base64.b64encode(hashlib.md5(data).digest()).decode()):
        raise ValueError("Copia GCS divergente; carga bloqueada")
    load = {
        "sourceUris": [uri], "sourceFormat": "NEWLINE_DELIMITED_JSON",
        "destinationTable": {"projectId": PROJECT, "datasetId": DATASET, "tableId": TABLE},
        "schema": {"fields": schema}, "writeDisposition": "WRITE_EMPTY",
        "createDisposition": "CREATE_IF_NEEDED", "maxBadRecords": 0,
        "destinationTableProperties": {"description":
            "Historico viu2, nome final autorizado pelo usuario; contrato sla-viu2-review-v1. "
            "Nao consolidado. Validacao de negocio pendente; "
            "NAO USAR EM KPI OU ML. Carga unica, sem agenda. Lacunas preservadas como NULL."},
    }
    job_id = "historical_sla_viu2_v1_" + DATA_SHA[:24]
    job_url = base + "/jobs/" + job_id + "?location=US"
    try:
        job = api.request(base + "/jobs", "POST", {
            "jobReference": {"projectId": PROJECT, "jobId": job_id, "location": "US"},
            "configuration": {"load": load, "labels": {"purpose": "review", "initiative": "pipeline-monday"}},
        })
    except HTTPError as error:
        if error.code != 409:
            raise
        job = api.request(job_url)
    for key in ("sourceUris", "destinationTable", "schema", "writeDisposition"):
        if job["configuration"]["load"].get(key) != load[key]:
            raise ValueError("Job existente divergente")
    deadline = time.monotonic() + 600
    while job["status"]["state"] != "DONE":
        if time.monotonic() > deadline:
            raise RuntimeError("Carga pendente: repetir este script reconcilia o mesmo job")
        time.sleep(2)
        job = api.request(job_url)
    if job["status"].get("errorResult"):
        raise RuntimeError("Carga recusada. Nenhuma tabela existente foi sobrescrita")
    table = api.request(base + "/datasets/" + DATASET + "/tables/" + TABLE)
    if int(table["numRows"]) != 17486 or table["schema"]["fields"] != schema:
        raise ValueError("Tabela nao reconciliada")
    print(json.dumps({"status": "historical_loaded_schema_and_count_verified", "table": PROJECT + "." + DATASET + "." + TABLE,
                      "rows": int(table["numRows"]), "job_id": job_id, "kpi_approved": False,
                      "expiration_time": table.get("expirationTime"), "source_sha256": DATA_SHA}, indent=2))


if __name__ == "__main__":
    try:
        publish(Path(__file__).resolve().parent)
    except Exception as error:
        print(json.dumps({"status": "historical_load_not_confirmed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
