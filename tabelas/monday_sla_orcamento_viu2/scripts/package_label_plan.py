"""Build a self-contained read-only preflight, never a production publisher."""

import gzip
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from audit_label_rebuild import reconcile
from historico_viu2.eligibility import frozen_inputs
from monday_comum.escopo_sla import filtrar_projetos


def main():
    root = Path(__file__).resolve().parents[3]
    archive = root / "runtime/archives/viu2_18393336134_20260921"
    source = (root / "runtime/validation/viu2_review_export_20260922_v1/review.ndjson.gz").read_bytes()
    target = (root / "runtime/validation/viu2_review_labels_v2/review.ndjson.gz").read_bytes()
    if hashlib.sha256(source).hexdigest() != "e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532":
        raise ValueError("Original divergente")
    if hashlib.sha256(target).hexdigest() != "0a8016b8dd633fb1e94bc5b7f27c38f3b485174b3f1f76eaa8fa4481c6cf5cea":
        raise ValueError("Candidata divergente")
    inputs = frozen_inputs(lambda name: (archive / name).read_bytes())
    old = filtrar_projetos([json.loads(x) for x in gzip.decompress(source).splitlines()], inputs)
    new = [json.loads(x) for x in gzip.decompress(target).splitlines()]
    reconcile(old, new)
    if filtrar_projetos(new, inputs) != new:
        raise ValueError("Escopo divergente")
    baseline = gzip.compress(b"".join((json.dumps(r, ensure_ascii=False) + "\n").encode() for r in old), mtime=0)
    files = {"before.ndjson.gz": baseline, "after.ndjson.gz": target,
             "schema.json": (root / "runtime/validation/viu2_review_labels_v2/schema.json").read_bytes(),
             "plan_label_migration.py": Path(__file__).with_name("plan_label_migration.py").read_bytes()}
    files["manifest.json"] = json.dumps({"target": "gglobo-viu-dados-hdg-prd:viu_agenciamento.monday_sla_orcamento_viu2",
        "mode": "read_only_plan", "files": {k: hashlib.sha256(v).hexdigest() for k, v in files.items()}}).encode()
    output = root / "runtime/viu2-rotulos-preflight-20260923-v1.zip"
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as zipped:
        for name, data in files.items():
            zipped.writestr(name, data)
    with ZipFile(output) as zipped:
        if zipped.testzip() or any(zipped.read(n) != b for n, b in files.items()):
            raise ValueError("ZIP nao reconciliado")
    print(json.dumps({"file": str(output), "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                      "apply_available": False, "cloud_modified": False}))


if __name__ == "__main__":
    main()
