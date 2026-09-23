"""Read-only supplemental rescue around unresolved batches. Original archive unchanged."""

import argparse
import json
from datetime import timedelta
from pathlib import Path

from dotenv import dotenv_values
from historico_viu2.sla import load_evidence
from monday_log_viu2.archive import LOG_QUERY, BoardArchive, encode
from sls_orcamento_ppd.clients.curl_session import CurlSession
from sls_orcamento_ppd.clients.monday_client import MondayClient
from sls_orcamento_ppd.config import Settings
from sls_orcamento_ppd.utils.time import parse_timestamp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--report", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise ValueError("Use um destino novo; não sobrescrever evidências")
    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    references = [r for r in report["pending_references"]
                  if r["reason"] == "missing_individual_without_value"]
    if not references:
        raise ValueError("Nenhuma referência selecionada")
    _, _, _, records, _, _ = load_evidence(args.archive)
    index = {str(r["id"]): r for r in records}
    days = {parse_timestamp(index[r["event_id"]]["created_at"]).replace(
        hour=0, minute=0, second=0, microsecond=0) for r in references}
    ids = sorted({r["item_id"] for r in references})
    credentials = dotenv_values(args.env_file)
    token = credentials.get("TOKEN_MONDAY_VIU2") or credentials.get("MONDAY_API_TOKEN")
    if credentials.get("BOARDS_VIU2", "18393336134") != "18393336134":
        raise ValueError("Quadro viu2 configurado incorretamente")
    if not token:
        raise ValueError("Credencial viu2 ausente")
    settings = Settings(_env_file=None, MONDAY_API_TOKEN=token, MONDAY_BOARD_ID=18393336134)
    client = MondayClient(settings, session=CurlSession())
    # Verify live identity before requesting any board data.
    account = client.query("query { me { account { id } } }", {})
    if str(account["me"]["account"]["id"]) != "5890468":
        raise ValueError("Credencial não corresponde à conta viu2")
    print("Conta viu2 confirmada; iniciando consultas somente de leitura.", flush=True)

    class TargetedArchive(BoardArchive):
        def capture(self, name, query, variables):
            if query == LOG_QUERY:
                query = query.replace("$limit: Int!", "$items: [ID!]!, $limit: Int!")
                query = query.replace("activity_logs(limit:", "activity_logs(item_ids: $items, limit:")
                variables = {**variables, "items": ids}
            return super().capture(name, query, variables)

    archive = TargetedArchive(client, output, "viu2")
    manifest = {"status": "in_progress", "source": "viu2", "account_id": "5890468",
                "board_id": "18393336134", "item_ids": ids,
                "scope": "Selected items; UTC days containing missing-value batches only",
                "not_a_full_board_rescue": True}
    try:
        archive.capture("account.json.gz", "query { me { account { id } } }", {})
        for day in sorted(days):
            archive.window(day, day + timedelta(days=1))
        manifest.update(archive.verify_events())
        manifest["status"] = "complete_targeted_window_review"
    finally:
        manifest.update(files=archive.inventory, accepted_log_pages=archive.accepted,
                        completed_windows=archive.windows)
        with (output / "targeted_manifest.json").open("xb") as handle:
            handle.write(encode(manifest))
    print(json.dumps({"status": manifest["status"], "items": len(ids), "days": len(days),
                      "events": manifest.get("unique_events"), "source_changed": False}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"event": "targeted_rescue_failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
