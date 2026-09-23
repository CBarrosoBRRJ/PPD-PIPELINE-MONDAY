"""Freeze item context needed to interpret the rescued log; never changes Monday."""

import argparse
import json
from datetime import UTC, datetime

from dotenv import dotenv_values
from monday_log_viu2.archive import BoardArchive, encode
from sls_orcamento_ppd.clients.curl_session import CurlSession
from sls_orcamento_ppd.clients.monday_client import ITEM_FIELDS, MondayClient
from sls_orcamento_ppd.config import Settings
from sls_orcamento_ppd.utils.time import iso


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    token = dotenv_values(args.env_file).get("MONDAY_API_TOKEN")
    settings = Settings(_env_file=None, MONDAY_API_TOKEN=token, MONDAY_BOARD_ID=18393336134)
    archive = BoardArchive(MondayClient(settings, session=CurlSession()), args.output, "viu2")
    account = archive.capture("account.json.gz", "query { me { account { id } } }", {})
    if str(account["me"]["account"]["id"]) != "5890468":
        raise ValueError("Conta diferente do viu2")
    board = archive.capture(
        "board.json.gz", "query { boards(ids:[18393336134]) { id items_count } }", {}
    )["boards"][0]
    cursor = None
    cursors = set()
    item_ids = set()
    person_ids = set()
    page_number = 1
    while True:
        if cursor:
            query = "query ($cursor: String!) { next_items_page(cursor:$cursor,limit:500) { cursor items { " + ITEM_FIELDS + " } } }"
            data = archive.capture(f"items_{page_number:04d}.json.gz", query, {"cursor": cursor})
            page = data["next_items_page"]
        else:
            query = "query { boards(ids:[18393336134]) { items_page(limit:500) { cursor items { " + ITEM_FIELDS + " } } } }"
            data = archive.capture(f"items_{page_number:04d}.json.gz", query, {})
            page = data["boards"][0]["items_page"]
        for item in page["items"]:
            if item["id"] in item_ids:
                raise ValueError("Item repetido na paginacao")
            item_ids.add(item["id"])
            for column in item["column_values"]:
                if column.get("type") == "people" and column.get("value"):
                    value = json.loads(column["value"])
                    person_ids.update(str(p["id"]) for p in value.get("personsAndTeams", [])
                                      if p.get("kind") == "person")
        print(f"Contexto: {len(item_ids)} itens preservados", flush=True)
        cursor = page.get("cursor")
        if not cursor:
            break
        if cursor in cursors:
            raise ValueError("Cursor repetido")
        cursors.add(cursor)
        page_number += 1
    if len(item_ids) != int(board["items_count"]):
        raise ValueError("Contagem de itens nao reconciliada")
    people = sorted(person_ids)
    for offset in range(0, len(people), 100):
        archive.capture(
            f"people_{offset:04d}.json.gz",
            "query ($ids:[ID!]) { users(ids:$ids) { id name } }",
            {"ids": people[offset:offset + 100]},
        )
    manifest = {"status": "complete_current_item_context", "source": "viu2",
                "board_id": "18393336134", "items": len(item_ids),
                "referenced_people": len(person_ids), "files": archive.inventory,
                "captured_at": iso(datetime.now(UTC)),
                "limitation": "Current visible active items, not historical attributes at migration."}
    (archive.directory / "context_manifest.json").write_bytes(encode(manifest))
    print("Contexto concluido.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Contexto incompleto: " + type(exc).__name__, flush=True)
        raise SystemExit(1) from None
