"""Compare verified supplementary responses with the frozen rescue; never merge in place."""

import argparse
import json
from pathlib import Path

from historico_viu2.reconciliation import audit_status_batches
from historico_viu2.sla import load_evidence, verified_envelope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--supplement", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Relatório existente")
    _, _, _, raw, _, _ = load_evidence(args.archive)
    original = {str(r["id"]): r for r in raw}
    manifest = json.loads((args.supplement / "targeted_manifest.json").read_bytes())
    if manifest["status"] != "complete_targeted_window_review" or manifest["account_id"] != "5890468":
        raise ValueError("Complemento incompleto ou de outra conta")
    added, changed, seen = {}, set(), {}
    for name in manifest["files"]:
        envelope = verified_envelope(args.supplement, name, manifest["files"])
        if name not in manifest["accepted_log_pages"]:
            continue
        for row in envelope["response"]["boards"][0]["activity_logs"]:
            if str(row["account_id"]) != "5890468":
                raise ValueError("Conta divergente")
            identity = str(row["id"])
            if identity in seen and seen[identity] != row:
                raise ValueError("Evento conflitante no complemento")
            seen[identity] = row
            if identity not in original:
                added[identity] = row
            elif original[identity] != row:
                changed.add(identity)
    if len(seen) != manifest["unique_events"]:
        raise ValueError("Contagem divergente")
    audit = audit_status_batches(raw + list(added.values()))
    report = {"supplement_events": len(seen), "new_event_ids": len(added),
              "existing_event_ids_with_changed_payload": len(changed),
              "batch_categories_after_additions": audit["categories"],
              "conflicting_event_ids": sorted(changed), "publication_ready": False,
              "source_modified": False, "original_archive_modified": False}
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != "conflicting_event_ids"}))


if __name__ == "__main__":
    main()
