"""Read-only trajectory audit of a checksum-verified NDJSON gzip snapshot."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from monday_sla_orcamento.trajectory import audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    content = args.snapshot.read_bytes()
    if hashlib.sha256(content).hexdigest() != args.sha256:
        raise ValueError("Snapshot: checksum divergente")
    rows = [json.loads(line) for line in gzip.decompress(content).splitlines() if line.strip()]
    report = audit(rows)
    report.pop("details")
    report.update(snapshot_sha256=args.sha256, cloud_modified=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
