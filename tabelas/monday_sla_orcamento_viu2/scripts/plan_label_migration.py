"""Read-only Cloud Shell preflight. No apply mode, cloud writes or credentials files."""

import gzip
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

PROJECT = "gglobo-viu-dados-hdg-prd"
TABLE = PROJECT + ":viu_agenciamento.monday_sla_orcamento_viu2"
CONTROL = "gs://" + PROJECT + "-ppd-pipeline-monday/consolidado/diario/control.json"


def command(*args):
    return json.loads(subprocess.check_output(args, text=True))


def fingerprint(rows, schema):
    normalized = []
    for source in rows:
        if set(source) != {f["name"] for f in schema}:
            raise ValueError("Campos divergentes")
        row = dict(source)
        for field in schema:
            key, kind = field["name"], field["type"]
            value = row[key]
            if value is None:
                continue
            if kind == "TIMESTAMP":
                at = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if at.utcoffset() is None:
                    raise ValueError("Timestamp sem fuso")
                row[key] = at.astimezone(UTC).isoformat(timespec="microseconds")
            elif kind == "DATETIME":
                row[key] = datetime.fromisoformat(value).isoformat(timespec="microseconds")
            elif kind in {"FLOAT", "FLOAT64"}:
                row[key] = float(value)
        normalized.append(row)
    normalized.sort(key=lambda r: r["interval_id"])
    return hashlib.sha256(json.dumps(normalized, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def load_package(root):
    manifest = json.loads((root / "manifest.json").read_bytes())
    if manifest["target"] != TABLE or manifest["mode"] != "read_only_plan":
        raise ValueError("Pacote de outro destino")
    files = {}
    for name in ("before.ndjson.gz", "after.ndjson.gz", "schema.json"):
        data = (root / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != manifest["files"][name]:
            raise ValueError("Checksum divergente")
        files[name] = data
    schema = json.loads(files["schema.json"])
    old, new = [[json.loads(line) for line in gzip.decompress(files[name]).splitlines()]
                for name in ("before.ndjson.gz", "after.ndjson.gz")]
    before = {r["interval_id"]: r for r in old}
    after = {r["interval_id"]: r for r in new}
    if len(before) != len(old) or len(after) != len(new) or before.keys() != after.keys():
        raise ValueError("Conjunto de chaves divergente")
    for key, row in after.items():
        changed = {f for f in row if row[f] != before[key][f]}
        if changed - {"status_nome", "qualidade_rotulo", "pendencias_json"}:
            raise ValueError("Campo protegido alterado")
        if row["status_nome"] != before[key]["status_nome"] and (
                before[key]["status_nome"] is not None or not row["status_nome"]):
            raise ValueError("Rotulo observado sobrescrito")
    return schema, old, new


def run(root):
    schema, old, new = load_package(root)
    before = command("bq", "show", "--format=prettyjson", TABLE)
    if before["schema"]["fields"] != schema or before.get("expirationTime"):
        raise ValueError("Schema ou expiracao inesperados")
    data = command("bq", "--project_id=" + PROJECT, "--format=json", "query",
                   "--location=US", "--use_legacy_sql=false", "--use_cache=false",
                   "--max_rows=100000", "--maximum_bytes_billed=104857600",
                   "SELECT TO_JSON_STRING(t) AS registro FROM `" + TABLE.replace(":", ".") + "` t")
    rows = [json.loads(r["registro"]) for r in data]
    after = command("bq", "show", "--format=prettyjson", TABLE)
    if before["etag"] != after["etag"] or len(rows) != int(after["numRows"]):
        raise ValueError("Tabela mudou durante leitura")
    if fingerprint(rows, schema) != fingerprint(old, schema):
        raise ValueError("Historico remoto difere da base auditada")
    control = command("gcloud", "storage", "cat", CONTROL)
    if control.get("pending") is not None:
        raise ValueError("Consolidada com publicacao pendente")
    return {"status": "read_only_plan_verified", "target": TABLE,
            "rows_before": len(old), "rows_after": len(new),
            "expected_modified": after["lastModifiedTime"],
            "before_fingerprint": fingerprint(old, schema),
            "after_fingerprint": fingerprint(new, schema),
            "consolidated_identity": control.get("identity"),
            "consolidated_active_fields": sorted((control.get("active") or {}).keys()),
            "cloud_modified": False, "apply_available": False}


if __name__ == "__main__":
    try:
        print(json.dumps(run(Path(__file__).resolve().parent), indent=2))
    except Exception as error:
        print(json.dumps({"status": "plan_not_confirmed", "error_type": type(error).__name__}))
        if isinstance(error, ValueError):
            print(str(error))
        raise SystemExit(1) from None
