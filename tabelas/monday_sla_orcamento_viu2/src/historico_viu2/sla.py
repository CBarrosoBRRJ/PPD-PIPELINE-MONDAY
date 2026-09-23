"""Offline, immutable SLA candidate from verified viu2 evidence. Never publishes."""

import gzip
import json
from collections import Counter
from pathlib import Path

from monday_log_viu2.archive import digest
from sls_orcamento_ppd.config import Settings
from sls_orcamento_ppd.db.bq import public_schema
from sls_orcamento_ppd.db.checkpoint import canonical_json
from sls_orcamento_ppd.models.bq_consumption import digest as public_digest
from sls_orcamento_ppd.models.bq_consumption import project
from sls_orcamento_ppd.models.consumption import GOLD
from sls_orcamento_ppd.services.extract import discover, obj, parse_activity, snapshot
from sls_orcamento_ppd.services.gold import build_gold
from sls_orcamento_ppd.services.transform import transform
from sls_orcamento_ppd.utils.time import parse_timestamp


def verified_envelope(directory, filename, inventory):
    root = Path(directory).resolve()
    path = (root / filename).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Arquivo fora do resgate")
    content = path.read_bytes()
    if digest(content) != inventory[filename]["sha256"]:
        raise ValueError("Checksum divergente no resgate")
    envelope = json.loads(gzip.decompress(content))
    if envelope["source"] != "viu2" or str(envelope["board_id"]) != "18393336134":
        raise ValueError("Origem divergente no resgate")
    return envelope


def load_evidence(directory):
    directory = Path(directory)
    manifest = json.loads((directory / "manifest.json").read_bytes())
    context = json.loads((directory / "context/context_manifest.json").read_bytes())
    if (
        manifest["status"] != "complete_available_api_history"
        or manifest["source"] != "viu2"
        or str(manifest["account_id"]) != "5890468"
        or str(manifest["board_id"]) != "18393336134"
        or context["status"] != "complete_current_item_context"
        or context["source"] != "viu2"
        or str(context["board_id"]) != "18393336134"
    ):
        raise ValueError("Resgate incompleto ou origem incorreta")
    account = verified_envelope(directory, "account.json.gz", manifest["files"])
    if str(account["response"]["me"]["account"]["id"]) != "5890468":
        raise ValueError("Conta incorreta no arquivo verificado")
    board = verified_envelope(directory, "board.json.gz", manifest["files"])["response"]["boards"][0]
    records = {}
    for filename in manifest["accepted_log_pages"]:
        envelope = verified_envelope(directory, filename, manifest["files"])
        for row in envelope["response"]["boards"][0]["activity_logs"]:
            if str(row["account_id"]) != "5890468":
                raise ValueError("Conta divergente no evento")
            key = str(row["id"])
            if key in records and records[key] != row:
                raise ValueError("Evento duplicado conflitante")
            records[key] = row
    if len(records) != manifest["unique_events"]:
        raise ValueError("Contagem de eventos divergente")
    items, people = {}, {}
    for filename in context["files"]:
        envelope = verified_envelope(directory / "context", filename, context["files"])
        response = envelope["response"]
        if filename.startswith("items_"):
            page = response.get("next_items_page") or response["boards"][0]["items_page"]
            for item in page["items"]:
                if item["id"] in items:
                    raise ValueError("Item repetido no contexto")
                items[item["id"]] = (item, parse_timestamp(envelope["captured_at"]))
        elif filename.startswith("people_"):
            for person in response["users"]:
                people[str(person["id"])] = {
                    "person_id": str(person["id"]), "person_name": person["name"], "email": None,
                }
    if len(items) != context["items"]:
        raise ValueError("Contagem de itens divergente")
    return manifest, context, board, list(records.values()), list(items.values()), list(people.values())


def build_candidate(directory, destination, cutoff):
    """Cut is exclusive. Unknown batch semantics block release, not evidence rescue."""
    if cutoff.utcoffset() is None:
        raise ValueError("Corte exige fuso explícito")
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Destino já existe; fotografia não pode ser sobrescrita")
    manifest, context, board, raw, items, persons = load_evidence(directory)
    at = parse_timestamp(context["captured_at"])
    if not parse_timestamp(board["created_at"]) < cutoff <= at:
        raise ValueError("Corte fora do período do resgate")
    settings = Settings(
        _env_file=None, MONDAY_BOARD_ID=18393336134, MONDAY_STATUS_COLUMN_ID="status_19",
        bq_table="sla_orcamento_viu2",
    )
    mapping, statuses, labels = discover(board, settings)
    snapshots = [snapshot(item, mapping, labels, settings, captured) for item, captured in items]
    names = {p["person_id"]: p["person_name"] for p in persons}
    roles = {c["id"]: c["title"] for c in board["columns"]}
    for snap in snapshots:
        for person in snap["pessoas_json"]:
            person["name"] = names.get(person["id"])
            person["role"] = roles[person["source_column_id"]]
    events, unsupported = [], Counter()
    for row in raw:
        data = obj(row["data"])
        if data.get("column_id") != settings.monday_status_column_id:
            continue
        parsed = parse_activity(row, settings, at)
        if parsed is not None:
            if parsed["event_at_utc"] < cutoff:
                events.append(parsed)
        elif parse_timestamp(row["created_at"]) < cutoff:
            unsupported[row["event"]] += 1
    payload = transform(events, snapshots, statuses, settings, at,
                        {s["item_id"] for s in snapshots if s["is_active"]})
    metrics = build_gold(payload, snapshots, board, mapping, [], persons, settings, at, cutoff=cutoff)
    payload["bronze_monday_item_snapshot_raw"] = snapshots
    payload["bronze_monday_board_schema_raw"] = [{"snapshot_at": at, "raw_data": board}]
    public = project(payload, settings)
    rows = public[GOLD]
    report = {
        "status": "draft_not_published", "table": "sla_orcamento_viu2",
        "source_environment": "viu2", "source_account_id": manifest["account_id"],
        "board_id": 18393336134, "cutoff_exclusive": cutoff.isoformat(),
        "snapshot_captured_at": context["captured_at"],
        "raw_events": len(raw), "status_events_before_cut": len(events),
        "unsupported_status_event_types": dict(unsupported),
        "publication_blockers": ["review_draft_quality"]
            + (["reconcile_batch_status_events"] if unsupported else []),
        "rows": len(rows), "public_digest": public_digest(rows),
        "source_manifest_sha256": digest((Path(directory) / "manifest.json").read_bytes()),
        "context_manifest_sha256": digest((Path(directory) / "context/context_manifest.json").read_bytes()),
        "write_disposition": "WRITE_EMPTY", "scheduled": False,
        "limitation": "Cadastro observado na coleta, não no corte; IDs entre contas não reconciliados.",
        **metrics,
    }
    destination.mkdir(parents=True, exist_ok=False)
    output = destination / "sla_orcamento_viu2.ndjson.gz"
    with output.open("xb") as handle, gzip.GzipFile(fileobj=handle, mode="wb", mtime=0) as stream:
        for row in rows:
            stream.write(canonical_json(row) + b"\n")
    report["sha256"] = digest(output.read_bytes())
    for name, content in {
        "schema.json": [field.to_api_repr() for field in public_schema()],
        "calendar.json": public["calendar"],
        "quality.json": payload["data_quality_issue"],
        "candidate_manifest.json": report,
    }.items():
        with (destination / name).open("xb") as stream:
            stream.write(canonical_json(content))
    return report
