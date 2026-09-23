"""Read-only status evidence for cross-account validation, bounded by saved context."""

import argparse
import gzip
import hashlib
import json
from datetime import timedelta
from pathlib import Path

from dotenv import dotenv_values
from monday_log_viu2.archive import LOG_QUERY, BoardArchive, encode
from sls_orcamento_ppd.clients.curl_session import CurlSession
from sls_orcamento_ppd.clients.monday_client import MondayClient
from sls_orcamento_ppd.config import Settings
from sls_orcamento_ppd.utils.time import iso, parse_timestamp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--env-file", default=".env")
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Destino existente; preservar")
    content = args.context.read_bytes()
    if hashlib.sha256(content).hexdigest() != args.context.with_suffix(".sha256").read_text().strip():
        raise ValueError("Contexto corrompido")
    context = json.loads(gzip.decompress(content))
    if context["account_id"] != "21453629" or str(context["board"]["id"]) != "18429499488":
        raise ValueError("Contexto de outra origem")
    token = dotenv_values(args.env_file).get("TOKEN_MONDAY")
    if not token:
        raise ValueError("Credencial ausente")
    settings = Settings(_env_file=None, MONDAY_API_TOKEN=token, MONDAY_BOARD_ID=18429499488)
    client = MondayClient(settings, session=CurlSession())
    account = client.query("query { me { account { id } } }", {})
    if str(account["me"]["account"]["id"]) != "21453629":
        raise ValueError("Conta incorreta")

    class StatusArchive(BoardArchive):
        def capture(self, name, query, variables):
            if query == LOG_QUERY:
                query = query.replace("activity_logs(limit:", 'activity_logs(column_ids:["status_19"],limit:')
            return super().capture(name, query, variables)

    archive = StatusArchive(client, args.output, "globocorp")
    start = parse_timestamp(context["board"]["created_at"]).replace(microsecond=0)
    end = parse_timestamp(context["captured_at"])
    manifest = {"status": "incomplete", "account_id": "21453629", "board_id": "18429499488",
                "source": "globocorp", "column_id": "status_19", "requested_from": iso(start),
                "requested_to": iso(end), "context_sha256": hashlib.sha256(content).hexdigest()}
    try:
        archive.capture("account.json.gz", "query { me { account { id } } }", {})
        edge = end
        while edge > start:
            lower = max(start, edge - timedelta(days=7))
            archive.window(lower, edge)
            edge = lower
        manifest.update(archive.verify_events())
        manifest["status"] = "complete_available_status_history"
    finally:
        manifest.update(files=archive.inventory, accepted_log_pages=archive.accepted)
        with (args.output / "manifest.json").open("xb") as handle:
            handle.write(encode(manifest))
    print(json.dumps({k: manifest[k] for k in ("status", "unique_events", "requested_to")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"event": "capture_failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
