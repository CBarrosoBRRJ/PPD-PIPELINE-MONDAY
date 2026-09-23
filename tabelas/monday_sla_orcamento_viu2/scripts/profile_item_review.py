"""Generate private item-level triage from verified rescue; no network or publication."""

import argparse
import json
from pathlib import Path

from historico_viu2.reconciliation import profile_item_review
from historico_viu2.sla import load_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Relatório existente não será sobrescrito")
    manifest, _, _, raw, items, _ = load_evidence(args.archive)
    report = profile_item_review(
        raw, [item["id"] for item, _ in items],
        account_id=manifest["account_id"], board_id=manifest["board_id"],
    )
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
