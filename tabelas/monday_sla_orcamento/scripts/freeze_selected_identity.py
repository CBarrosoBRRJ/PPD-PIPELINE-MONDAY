"""Recompute matching from checked source contexts before freezing private policy map."""

import gzip
import hashlib
import json
from pathlib import Path

from historico_viu2.matching import find_candidates
from historico_viu2.selected_identity import select_identity
from historico_viu2.sla import verified_envelope


def main():
    root = Path("runtime")
    old_root = root / "archives/viu2_18393336134_20260921"
    old_manifest = json.loads((old_root / "manifest.json").read_bytes())
    old_board = verified_envelope(old_root, "board.json.gz", old_manifest["files"])["response"]["boards"][0]
    context_root = old_root / "context"
    old_context_raw = (context_root / "context_manifest.json").read_bytes()
    context_manifest = json.loads(old_context_raw)
    items = []
    for name in context_manifest["files"]:
        if name.startswith("items_"):
            response = verified_envelope(context_root, name, context_manifest["files"])["response"]
            page = response.get("next_items_page") or response["boards"][0]["items_page"]
            items.extend(page["items"])
    new_path = root / "validation/project_matching_20260922_v3/globocorp_context.json.gz"
    raw = new_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != new_path.with_suffix(".sha256").read_text().strip():
        raise ValueError("Contexto novo: checksum divergente")
    new = json.loads(gzip.decompress(raw))
    if new["account_id"] != "21453629" or str(new["board"]["id"]) != "18429499488":
        raise ValueError("Contexto novo: escopo divergente")
    report = find_candidates(old_board, items, new["board"], new["items"])
    report_path = root / "validation/project_matching_20260922_v3/matching_report.json"
    saved_raw = report_path.read_bytes()
    saved = json.loads(saved_raw)
    if report["candidates"] != saved["candidates"]:
        raise ValueError("Correspondências divergentes da análise anterior")
    result = select_identity(report, [i["id"] for i in items], [i["id"] for i in new["items"]])
    result["evidence"] = {
        "matching_report_sha256": hashlib.sha256(saved_raw).hexdigest(),
        "old_context_manifest_sha256": hashlib.sha256(old_context_raw).hexdigest(),
        "new_context_sha256": hashlib.sha256(raw).hexdigest(),
        "new_context_captured_at": new["captured_at"],
        "policy_authorization": "User accepted combined-field matching and exclusion of unresolved pairs in this conversation; no claim of individual review.",
    }
    destination = root / "validation/selected_identity_20260922_v1"
    destination.mkdir(exist_ok=False)
    content = gzip.compress(json.dumps(result, ensure_ascii=False, sort_keys=True).encode(), mtime=0)
    with (destination / "selected_identity.json.gz").open("xb") as stream:
        stream.write(content)
    if json.loads(gzip.decompress((destination / "selected_identity.json.gz").read_bytes())) != result:
        raise ValueError("Releitura divergente")
    sha = hashlib.sha256(content).hexdigest()
    with (destination / "selected_identity.sha256").open("x") as stream:
        stream.write(sha + "\n")
    print(json.dumps({**result["summary"], "sha256": sha}))


if __name__ == "__main__":
    main()
