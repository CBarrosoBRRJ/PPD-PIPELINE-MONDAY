"""Build private normalized evidence from frozen archive; never publishes."""

import argparse
import json
from pathlib import Path

from historico_viu2.observations import build_observations
from historico_viu2.sla import load_evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Saída existente não será sobrescrita")
    manifest, _, _, raw, _, _ = load_evidence(args.archive)
    report = build_observations(raw, account_id=manifest["account_id"], board_id=manifest["board_id"])
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
