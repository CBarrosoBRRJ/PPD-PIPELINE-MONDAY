"""Read a private observation artifact and write candidate passages; no network."""

import argparse
import hashlib
import json
from pathlib import Path

from historico_viu2.passages import build_passages


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Saída existente não será sobrescrita")
    raw = args.observations.read_bytes()
    report = build_passages(json.loads(raw))
    report["source_observations_sha256"] = hashlib.sha256(raw).hexdigest()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
