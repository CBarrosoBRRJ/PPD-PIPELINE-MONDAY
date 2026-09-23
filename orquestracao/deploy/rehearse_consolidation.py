"""Read-only replay: new scope only removes projects from the initial snapshot."""

import gzip
import hashlib
import json
import runpy
from pathlib import Path

from monday_comum.escopo_sla import filtrar_projetos
from monday_sla_orcamento.consolidation import build
from monday_sla_orcamento.publication import HISTORY_SHA, INITIAL_SHA, MAP_SHA, fingerprint


def checked(path, expected):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Rehearsal input checksum mismatch")
    return gzip.decompress(raw)


def main():
    root = Path(__file__).resolve().parents[2]
    old = [json.loads(line) for line in checked(
        root / "runtime/validation/viu2_review_export_20260922_v1/review.ndjson.gz", HISTORY_SHA).splitlines()]
    mapping = json.loads(checked(
        root / "runtime/validation/selected_identity_20260922_v1/selected_identity.json.gz", MAP_SHA))
    new = json.loads(checked(Path("C:/Users/CCMB/Downloads/globocorp-para-consolidacao.json.gz"),
                            "3f3d07cef374f11b3b6811364e62099ca81c4a517026dbdefbc7798f29ec83e7"))
    expected = [json.loads(line) for line in checked(
        root / "runtime/validation/consolidated_20260922_v3/consolidated.ndjson.gz", INITIAL_SHA).splitlines()]
    source_loader = runpy.run_path(str(root / "compartilhado/scripts/avaliar_escopo.py"))["sources"]
    _, _, _, old_inputs, new_inputs = source_loader(root)
    rows, report = build(old, filtrar_projetos(new["rows"], new_inputs), mapping, old_inputs=old_inputs)
    retained = {row["projeto_id"] for row in rows}
    expected = [row for row in expected if row["projeto_id"] in retained]
    if not rows or fingerprint(rows) != fingerprint(expected):
        raise ValueError("Rehearsal changed retained project contents")
    print(json.dumps({"status": "retained_projects_identical", "rows": len(rows),
                      "projects": report["projects"], "fingerprint": fingerprint(rows),
                      "gcp_modified": False}))


if __name__ == "__main__":
    main()
