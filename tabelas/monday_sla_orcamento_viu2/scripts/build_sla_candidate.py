"""Build an offline draft only; no cloud writes and no scheduled execution."""

import argparse
import json
from datetime import datetime

from historico_viu2.sla import build_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cutoff", required=True, help="ISO-8601 com hora e fuso; limite exclusivo")
    args = parser.parse_args()
    result = build_candidate(args.archive, args.output, datetime.fromisoformat(args.cutoff))
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))


if __name__ == "__main__":
    main()
