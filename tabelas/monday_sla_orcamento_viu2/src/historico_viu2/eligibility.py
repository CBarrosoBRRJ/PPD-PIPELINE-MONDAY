"""Read the already captured viu2 input context, verifying its pinned checksums."""

import gzip
import hashlib
import json

from monday_comum.escopo_sla import coluna_input, ler_input

CONTEXT_SHA = "09c4ee9fa52bfce95882c2a7e187de2b92adfce139429802132a25568b1bceca"
BOARD_SHA = "b160485b57f30f0c1a80923324459882d0b1be05cb0789114e664c582b6e5c4e"


def frozen_inputs(read):
    def checked(path, sha, compressed=True):
        raw = read(path)
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError("Contexto viu2: checksum divergente")
        return json.loads(gzip.decompress(raw) if compressed else raw)
    manifest = checked("context/context_manifest.json", CONTEXT_SHA, False)
    board = checked("board.json.gz", BOARD_SHA)["response"]["boards"][0]
    if str(manifest["board_id"]) != "18393336134" or manifest["source"] != "viu2":
        raise ValueError("Contexto viu2: origem divergente")
    column = coluna_input(board)
    values = {}
    for name, info in manifest["files"].items():
        if not name.startswith("items_"):
            continue
        if "/" in name or "\\" in name:
            raise ValueError("Contexto viu2: caminho invalido")
        envelope = checked("context/" + name, info["sha256"])
        if str(envelope["board_id"]) != "18393336134" or envelope["source"] != "viu2":
            raise ValueError("Contexto viu2: pagina de outra origem")
        response = envelope["response"]
        page = response.get("next_items_page") or response["boards"][0]["items_page"]
        for item in page["items"]:
            key = (18393336134, int(item["id"]))
            if key in values:
                raise ValueError("Contexto viu2: item duplicado")
            values[key] = ler_input(column, item)
    if len(values) != manifest["items"]:
        raise ValueError("Contexto viu2: contagem divergente")
    return values
