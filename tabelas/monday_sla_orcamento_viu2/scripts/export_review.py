"""Export validated private review contract; never authorizes a BigQuery load."""

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from historico_viu2.review_contract import VERSION, project_review, schema, validate


def sha(content):
    return hashlib.sha256(content).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Destino existente não será sobrescrito")
    content = args.candidate.read_bytes()
    rows = project_review(json.loads(content))
    payload = gzip.compress(b"".join((json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                                   for row in rows), mtime=0)
    restored = [json.loads(line) for line in gzip.decompress(payload).splitlines()]
    validate(restored)
    if restored != rows:
        raise ValueError("Exportação não reconciliada")
    args.output.mkdir(parents=True, exist_ok=False)
    artifacts = {"review.ndjson.gz": payload,
                 "schema.json": json.dumps(schema(), indent=2).encode()}
    for name, data in artifacts.items():
        with (args.output / name).open("xb") as handle:
            handle.write(data)
    manifest = {"contract": VERSION, "rows": len(rows), "status": "validated_private_review_only",
                "source_candidate_sha256": sha(content), "publication_allowed": False,
                "kpi_approved_rows": 0, "daily_pipeline_modified": False,
                "files": {name: {"bytes": len(data), "sha256": sha(data)} for name, data in artifacts.items()},
                "blockers": ["historical_labels_and_schema", "business_eligibility", "project_identity_mapping",
                             "migration_boundary", "public_contract_migration_and_consumer_validation"]}
    with (args.output / "manifest.json").open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
    print(json.dumps({k: manifest[k] for k in ("contract", "rows", "status", "publication_allowed", "kpi_approved_rows")}))


if __name__ == "__main__":
    main()
