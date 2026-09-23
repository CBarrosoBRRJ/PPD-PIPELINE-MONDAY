"""Prepare typed NDJSON for BigQuery; no network or publication."""

import argparse
import json

from monday_log_viu2.structured import export

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--archive", required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args()
try:
    print(json.dumps(export(args.archive, args.output)), flush=True)
except Exception as exc:
    print("Exportacao bloqueada: " + type(exc).__name__, flush=True)
    raise SystemExit(1) from None
