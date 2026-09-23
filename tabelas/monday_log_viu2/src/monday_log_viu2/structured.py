"""Lossless typed projection of a verified archive, without applying a SLA cutoff."""

import gzip
import json
from pathlib import Path

from sls_orcamento_ppd.utils.time import iso, parse_timestamp

from .archive import digest, encode

SCHEMA = [
    {"name": name, "type": kind, "mode": mode}
    for name, kind, mode in [
        ("source_environment", "STRING", "REQUIRED"),
        ("source_account_id", "STRING", "REQUIRED"),
        ("board_id", "INTEGER", "REQUIRED"),
        ("event_id", "STRING", "REQUIRED"),
        ("event_account_id", "STRING", "REQUIRED"),
        ("event_type", "STRING", "REQUIRED"),
        ("entity", "STRING", "REQUIRED"),
        ("user_id", "STRING", "REQUIRED"),
        ("event_at_raw", "STRING", "REQUIRED"),
        ("event_at_utc", "TIMESTAMP", "NULLABLE"),
        ("item_id", "INTEGER", "NULLABLE"),
        ("column_id", "STRING", "NULLABLE"),
        ("data_raw", "STRING", "REQUIRED"),
        ("parse_warnings", "STRING", "REQUIRED"),
        ("captured_at", "TIMESTAMP", "REQUIRED"),
        ("archive_id", "STRING", "REQUIRED"),
        ("archive_file", "STRING", "REQUIRED"),
        ("raw_record_sha256", "STRING", "REQUIRED"),
    ]
]


def project(row, envelope, manifest, filename, archive_id):
    warnings = []
    try:
        timestamp = iso(parse_timestamp(row["created_at"]))
    except (TypeError, ValueError, OverflowError):
        timestamp = None
        warnings.append("unparsed_timestamp")
    try:
        payload = json.loads(row["data"])
        if not isinstance(payload, dict):
            raise ValueError
    except (TypeError, ValueError):
        payload = {}
        warnings.append("unparsed_data")
    raw_item = payload.get("pulse_id", payload.get("item_id"))
    item = None
    if raw_item is not None:
        if isinstance(raw_item, (int, str)) and not isinstance(raw_item, bool):
            text = str(raw_item)
            if text.isascii() and text.isdecimal() and 0 < int(text) < 2**63:
                item = int(text)
        if item is None:
            warnings.append("unparsed_item_id")
    column = payload.get("column_id")
    if column is not None and not isinstance(column, str):
        column = None
        warnings.append("unparsed_column_id")
    return {
        "source_environment": manifest["source"],
        "source_account_id": manifest["account_id"],
        "board_id": int(manifest["board_id"]),
        "event_id": str(row["id"]), "event_account_id": str(row["account_id"]),
        "event_type": row["event"], "entity": row["entity"], "user_id": str(row["user_id"]),
        "event_at_raw": str(row["created_at"]), "event_at_utc": timestamp,
        "item_id": item, "column_id": column, "data_raw": row["data"],
        "parse_warnings": ",".join(warnings), "captured_at": envelope["captured_at"],
        "archive_id": archive_id, "archive_file": filename,
        "raw_record_sha256": digest(encode(row)),
    }


def export(directory, destination):
    directory, destination = Path(directory), Path(destination)
    manifest = json.loads((directory / "manifest.json").read_bytes())
    if manifest["status"] != "complete_available_api_history":
        raise ValueError("Resgate incompleto; exportacao bloqueada")
    destination.mkdir(parents=True, exist_ok=True)
    final = destination / "log_monday_viu2.ndjson.gz"
    temporary = destination / "log_monday_viu2.ndjson.gz.partial"
    if final.exists() or temporary.exists():
        raise ValueError("Destino ja existe; nao sobrescrever historico")
    seen = {}
    warnings = 0
    event_types = {}
    with temporary.open("xb") as raw, gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as out:
        for filename in manifest["accepted_log_pages"]:
            content = (directory / filename).read_bytes()
            if digest(content) != manifest["files"][filename]["sha256"]:
                raise ValueError("Checksum divergente; exportacao bloqueada")
            envelope = json.loads(gzip.decompress(content))
            if envelope["source"] != manifest["source"] or envelope["board_id"] != manifest["board_id"]:
                raise ValueError("Origem divergente no arquivo")
            for row in envelope["response"]["boards"][0]["activity_logs"]:
                fingerprint = digest(encode(row))
                event_id = str(row["id"])
                if event_id in seen:
                    if seen[event_id] != fingerprint:
                        raise ValueError("Evento conflitante; exportacao bloqueada")
                    continue
                seen[event_id] = fingerprint
                result = project(row, envelope, manifest, filename, directory.name)
                warnings += bool(result["parse_warnings"])
                event_types[row["event"]] = event_types.get(row["event"], 0) + 1
                out.write(encode(result) + b"\n")
    if len(seen) != manifest["unique_events"]:
        raise ValueError("Contagem nao reconciliada com o arquivo bruto")
    temporary.rename(final)
    checksum = digest(final.read_bytes())
    (destination / "schema.json").write_bytes(encode(SCHEMA))
    report = {"status": "ready_for_one_time_load", "rows": len(seen),
              "rows_with_parse_warnings": warnings, "event_types": event_types,
              "sha256": checksum, "file": final.name,
              "source_manifest_sha256": digest((directory / "manifest.json").read_bytes()),
              "write_disposition": "WRITE_EMPTY", "published": False}
    (destination / "export_manifest.json").write_bytes(encode(report))
    return report
