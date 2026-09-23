"""Verify rescue and enrich private historical draft. No publication or credentials."""

import argparse
import hashlib
import json
from pathlib import Path

from historico_viu2.enrichment import enrich_passages
from historico_viu2.sla import load_evidence
from monday_comum.escopo_sla import coluna_input
from sls_orcamento_ppd.config import Settings
from sls_orcamento_ppd.services.extract import discover, snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Saída existente não será sobrescrita")
    manifest, _, board, raw, items, _ = load_evidence(args.archive)
    settings = Settings(_env_file=None, MONDAY_BOARD_ID=18393336134, MONDAY_STATUS_COLUMN_ID="status_19")
    mapping, _, labels = discover(board, settings)
    snapshots = [snapshot(item, mapping, labels, settings, at) for item, at in items]
    content = args.candidate.read_bytes()
    candidate = json.loads(content)
    if any(r["source_account_id"] != str(manifest["account_id"]) or
           r["source_board_id"] != str(manifest["board_id"]) for r in candidate["passages"]):
        raise ValueError("Candidato de outra origem")
    report = enrich_passages(candidate, raw, snapshots, labels, input_column=coluna_input(board))
    report["source_candidate_sha256"] = hashlib.sha256(content).hexdigest()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
