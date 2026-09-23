"""Capture new board read-only and compare to frozen viu2; private candidates only."""

import argparse
import gzip
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from dotenv import dotenv_values
from historico_viu2.matching import find_candidates
from historico_viu2.sla import verified_envelope
from sls_orcamento_ppd.clients.curl_session import CurlSession
from sls_orcamento_ppd.clients.monday_client import MondayClient
from sls_orcamento_ppd.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--new-context", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Destino existente não será sobrescrito")
    args.output.mkdir(parents=True, exist_ok=False)
    if args.new_context:
        content = args.new_context.read_bytes()
        if hashlib.sha256(content).hexdigest() != args.new_context.with_suffix(".sha256").read_text().strip():
            raise ValueError("Checksum do contexto divergente")
        new = json.loads(gzip.decompress(content))
    else:
        token = dotenv_values(args.env_file).get("TOKEN_MONDAY")
        if not token:
            raise ValueError("Credencial globocorp ausente")
        settings = Settings(_env_file=None, MONDAY_API_TOKEN=token, MONDAY_BOARD_ID=18429499488, MONDAY_PAGE_SIZE=500)
        client = MondayClient(settings, session=CurlSession())
        account = client.query("query { me { account { id } } }", {})
        if str(account["me"]["account"]["id"]) != "21453629":
            raise ValueError("Credencial não corresponde à conta globocorp")
        board = client.board()
        items = []
        for page in client.item_pages():
            items.extend(page)
            print(json.dumps({"new_context_items": len(items)}), flush=True)
        after = client.board()
        if len(items) != int(board["items_count"]) or board["items_count"] != after["items_count"]:
            raise ValueError("Contagem mudou durante captura; repetir em novo destino")
        new = {"account_id": "21453629", "board": board, "items": items,
               "captured_at": datetime.now(UTC).isoformat(), "scope": "current_visible_items"}
        content = gzip.compress(json.dumps(new, ensure_ascii=False).encode(), mtime=0)
    if new["account_id"] != "21453629" or str(new["board"]["id"]) != "18429499488":
        raise ValueError("Contexto de outra origem")
    with (args.output / "globocorp_context.json.gz").open("xb") as stream:
        stream.write(content)
    with (args.output / "globocorp_context.json.sha256").open("x") as stream:
        stream.write(hashlib.sha256(content).hexdigest())
    manifest = json.loads((args.archive / "manifest.json").read_bytes())
    account = verified_envelope(args.archive, "account.json.gz", manifest["files"])
    if str(account["response"]["me"]["account"]["id"]) != "5890468":
        raise ValueError("Resgate não corresponde à conta viu2")
    old_board = verified_envelope(args.archive, "board.json.gz", manifest["files"])["response"]["boards"][0]
    context_root = args.archive / "context"
    context = json.loads((context_root / "context_manifest.json").read_bytes())
    old_items = []
    for name in context["files"]:
        if name.startswith("items_"):
            response = verified_envelope(context_root, name, context["files"])["response"]
            page = response.get("next_items_page") or response["boards"][0]["items_page"]
            old_items.extend(page["items"])
    if len(old_items) != context["items"]:
        raise ValueError("Contagem do contexto viu2 divergente")
    report = find_candidates(old_board, old_items, new["board"], new["items"])
    report["new_context_sha256"] = hashlib.sha256(content).hexdigest()
    report["old_context_manifest_sha256"] = hashlib.sha256((context_root / "context_manifest.json").read_bytes()).hexdigest()
    report["globocorp_captured_at"] = new["captured_at"]
    with (args.output / "matching_report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"]), flush=True)
    print(json.dumps(report["field_statistics"], ensure_ascii=True), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(json.dumps({"event": "matching_failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
