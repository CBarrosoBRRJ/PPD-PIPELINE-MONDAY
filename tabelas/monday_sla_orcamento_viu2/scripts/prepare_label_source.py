"""Prepare immutable coordinator input, preserving evidence of excluded projects."""

import gzip
import hashlib
import json
from pathlib import Path

from audit_label_rebuild import reconcile
from historico_viu2.eligibility import frozen_inputs
from historico_viu2.review_contract import validate
from monday_comum.escopo_sla import filtrar_projetos


def merge_source(original, selected_before, selected_after):
    reconcile(selected_before, selected_after)
    replacements = {r["interval_id"]: r for r in selected_after}
    result = [replacements.get(r["interval_id"], r) for r in original]
    if len({r["interval_id"] for r in result}) != len(result):
        raise ValueError("Chaves duplicadas na fonte")
    if not replacements.keys() <= {r["interval_id"] for r in original}:
        raise ValueError("Candidata inclui chave fora da fonte")
    validate(result)
    return result


def main():
    root = Path(__file__).resolve().parents[3]
    base = root / "runtime/validation"
    archive = root / "runtime/archives/viu2_18393336134_20260921"
    old_blob = (base / "viu2_review_export_20260922_v1/review.ndjson.gz").read_bytes()
    new_blob = (base / "viu2_review_labels_v2/review.ndjson.gz").read_bytes()
    if hashlib.sha256(old_blob).hexdigest() != "e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532":
        raise ValueError("Fonte original divergente")
    if hashlib.sha256(new_blob).hexdigest() != "0a8016b8dd633fb1e94bc5b7f27c38f3b485174b3f1f76eaa8fa4481c6cf5cea":
        raise ValueError("Candidata divergente")
    old, new = [[json.loads(line) for line in gzip.decompress(blob).splitlines()]
                for blob in (old_blob, new_blob)]
    inputs = frozen_inputs(lambda name: (archive / name).read_bytes())
    result = merge_source(old, filtrar_projetos(old, inputs), new)
    if filtrar_projetos(result, inputs) != new:
        raise ValueError("Fonte do coordenador diverge da tabela candidata")
    content = gzip.compress(b"".join((json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                                   for r in result), mtime=0)
    out = base / "viu2_review_labels_v2/coordinator_source.ndjson.gz"
    with out.open("xb") as handle:
        handle.write(content)
    print(json.dumps({"source_rows": len(result), "public_rows": len(new),
                      "excluded_evidence_preserved": len(result) - len(new),
                      "sha256": hashlib.sha256(content).hexdigest(), "cloud_modified": False}))


if __name__ == "__main__":
    main()
