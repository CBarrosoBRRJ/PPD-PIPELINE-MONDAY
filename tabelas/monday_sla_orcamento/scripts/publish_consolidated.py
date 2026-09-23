"""Initial WRITE_EMPTY load only; no source mutations or daily scheduling."""

import base64
import gzip
import hashlib
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote

try:  # Standalone first-load ZIP, or installed workspace packages.
    from consolidation import FIELDS, timestamp, validate
    from publish_history import BUCKET, DATASET, PROJECT, GoogleAPI, gcloud, identity
except ModuleNotFoundError:
    from monday_log_viu2.publication import BUCKET, DATASET, PROJECT, GoogleAPI, gcloud, identity
    from monday_sla_orcamento.consolidation import FIELDS, timestamp, validate

TABLE = "monday_sla_orcamento"
SOURCES = {"monday_sla_orcamento_viu2", "monday_sla_orcamento_globocorp"}


def fingerprint(rows):
    normalized = []
    for row in rows:
        r = dict(row)
        for key, (kind, _) in FIELDS.items():
            if r[key] is not None and kind == "TIMESTAMP":
                r[key] = timestamp(r[key]).isoformat(timespec="microseconds")
            elif r[key] is not None and kind == "DATETIME":
                r[key] = datetime.fromisoformat(r[key]).isoformat(timespec="microseconds")
            elif r[key] is not None and kind == "FLOAT":
                r[key] = float(r[key])
        normalized.append(r)
    normalized.sort(key=lambda r: r["interval_id"])
    return hashlib.sha256(json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def publish(root):
    manifest = json.loads((root / "manifest.json").read_bytes())
    if manifest["destination"] != TABLE or set(manifest["expected_source_modified"]) != SOURCES:
        raise ValueError("Manifesto de outro destino")
    artifacts = {}
    for name in ("consolidated.ndjson.gz", "schema.json", "selected_identity.json.gz"):
        content = (root / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != manifest["files"][name]["sha256"]:
            raise ValueError("Artefato divergente")
        artifacts[name] = content
    rows = [json.loads(line) for line in gzip.decompress(artifacts["consolidated.ndjson.gz"]).splitlines()]
    validate(rows)
    if not rows or len(rows) != manifest["rows"]:
        raise ValueError("Contagem divergente/vazia")
    fields = json.loads(artifacts["schema.json"])
    api = GoogleAPI()
    identity(api)
    base = "https://bigquery.googleapis.com/bigquery/v2/projects/" + PROJECT
    if api.request(base + "/datasets/" + DATASET)["location"].upper() != "US":
        raise ValueError("Localizacao inesperada")

    def check_sources():
        for name in sorted(SOURCES):
            metadata = api.request(base + "/datasets/" + DATASET + "/tables/" + name)
            if metadata["lastModifiedTime"] != manifest["expected_source_modified"][name]:
                raise ValueError("Fonte mudou: reconstruir consolidado antes de publicar")

    check_sources()
    sha = manifest["files"]["consolidated.ndjson.gz"]["sha256"]
    prefix = "consolidado/primeira_carga/" + sha + "/"
    for name in (*artifacts, "manifest.json"):
        content = (root / name).read_bytes()
        uri = "gs://" + BUCKET + "/" + prefix + name
        gcloud("storage", "cp", "--no-clobber", str(root / name), uri, capture=False)
        remote = api.request("https://storage.googleapis.com/storage/v1/b/" + BUCKET + "/o/" + quote(prefix + name, safe=""))
        expected = base64.b64encode(hashlib.md5(content).digest()).decode()
        if int(remote["size"]) != len(content) or remote["md5Hash"] != expected:
            raise ValueError("Copia GCS divergente")
    check_sources()
    load = {
        "sourceUris": ["gs://" + BUCKET + "/" + prefix + "consolidated.ndjson.gz"],
        "destinationTable": {"projectId": PROJECT, "datasetId": DATASET, "tableId": TABLE},
        "sourceFormat": "NEWLINE_DELIMITED_JSON", "schema": {"fields": fields},
        "writeDisposition": "WRITE_EMPTY", "createDisposition": "CREATE_IF_NEEDED", "maxBadRecords": 0,
        "clustering": {"fields": ["projeto_id", "ambiente_origem", "item_id"]},
        "destinationTableProperties": {"description":
            "Trajetoria por projeto selecionado, somente passagens com entrada e ordem comprovadas. "
            "Validacao de negocio e continuidade pendentes: NAO homologado para KPI/ML. "
            "Carga inicial sem agenda; duracoes desconhecidas NULL; referencias sem data excluidas, preservadas nas origens."},
    }
    job_id = "consolidado_inicial_v1_" + sha[:28]
    job_url = base + "/jobs/" + job_id + "?location=US"
    try:
        job = api.request(base + "/jobs", "POST", {
            "jobReference": {"projectId": PROJECT, "jobId": job_id, "location": "US"},
            "configuration": {"load": load, "labels": {"initiative": "pipeline-monday", "validation": "pending"}},
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
        if time.monotonic() >= deadline:
            raise RuntimeError("Carga pendente: repetir para reconciliar mesmo job")
        time.sleep(2)
        job = api.request(job_url)
    if job["status"].get("errorResult"):
        raise RuntimeError("Carga recusada; nenhuma tabela nao vazia foi sobrescrita")
    table_url = base + "/datasets/" + DATASET + "/tables/" + TABLE
    metadata = api.request(table_url)
    if int(metadata["numRows"]) != len(rows) or metadata["schema"]["fields"] != fields:
        raise ValueError("Schema/quantidade remota divergentes")
    result = subprocess.check_output([
        "bq", "--project_id=" + PROJECT, "--format=json",
        "query", "--location=US", "--use_legacy_sql=false", "--use_cache=false",
        "--max_rows=100000", "--maximum_bytes_billed=104857600",
        "SELECT TO_JSON_STRING(t) AS registro FROM `" + PROJECT + "." + DATASET + "." + TABLE + "` AS t",
    ], text=True)
    actual = [json.loads(r["registro"]) for r in json.loads(result)]
    if (len(actual) != len(rows) or fingerprint(actual) != fingerprint(rows) or
            api.request(table_url)["lastModifiedTime"] != metadata["lastModifiedTime"]):
        raise ValueError("Conteudo remoto nao reconciliado")
    receipt = {"status": "loaded_and_content_verified", "table": PROJECT + "." + DATASET + "." + TABLE,
               "rows": len(rows), "projects": manifest["projects"], "job_id": job_id,
               "source_sha256": sha, "kpi_approved": False, "daily_integration_deployed": False,
               "expiration_time": metadata.get("expirationTime")}
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    try:
        publish(Path(__file__).resolve().parent)
    except Exception as error:
        print(json.dumps({"status": "consolidation_not_confirmed", "error_type": type(error).__name__}))
        if isinstance(error, (ValueError, RuntimeError)):
            print(str(error))
        raise SystemExit(1) from None
