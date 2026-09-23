"""Verify every rescued file and audit batches; no Monday/GCP writes."""

import argparse
import json
from pathlib import Path

from historico_viu2.reconciliation import audit_status_batches, profile_batch_coverage
from historico_viu2.sla import load_evidence
from monday_log_viu2.publication import local_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Relatório existente não será sobrescrito")
    files, export = local_files(args.archive)
    manifest, context, _, raw, items, _ = load_evidence(args.archive)
    report = audit_status_batches(raw)
    report.update(
        batch_coverage=profile_batch_coverage(raw, [item["id"] for item, _ in items]),
        files_verified=len(files), structured_rows=export["rows"],
        structured_sha256=export["sha256"], context_items=context["items"],
        source_account=manifest["account_id"], source_board=manifest["board_id"],
        readiness="blocked_pending_semantic_reconciliation" if report["review_required"] else "requires_business_review",
        cloud_changed=False,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "pending_references"}, ensure_ascii=True))


if __name__ == "__main__":
    main()
