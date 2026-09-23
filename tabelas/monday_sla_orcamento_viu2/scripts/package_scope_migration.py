"""Package only original treated SLA and its approved subset; no cloud access."""
import gzip
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from historico_viu2.eligibility import frozen_inputs
from historico_viu2.review_contract import validate
from monday_comum.escopo_sla import VERSION, filtrar_projetos


def main():
    root = Path(__file__).resolve().parents[3]
    review = root / "runtime/validation/viu2_review_export_20260922_v1"
    archive = root / "runtime/archives/viu2_18393336134_20260921"
    original = (review / "review.ndjson.gz").read_bytes()
    source_sha = "e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532"
    if hashlib.sha256(original).hexdigest() != source_sha:
        raise ValueError("Fonte original divergente")
    rows = [json.loads(line) for line in gzip.decompress(original).splitlines()]
    selected = filtrar_projetos(rows, frozen_inputs(lambda name: (archive / name).read_bytes()))
    validate(selected)
    if len(selected) != 14761 or VERSION != "escopo-sla-v3":
        raise ValueError("Recorte inesperado")
    content = b"".join((json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n").encode() for r in selected)
    files = {"original.ndjson.gz": original, "filtered.ndjson.gz": gzip.compress(content, mtime=0),
             "schema.json": (review / "schema.json").read_bytes(),
             "migrate_scope.py": (Path(__file__).parent / "migrate_scope.py").read_bytes(),
             "publish_history.py": (root / "tabelas/monday_log_viu2/src/monday_log_viu2/publication.py").read_bytes()}
    files["scope_manifest.json"] = json.dumps({"table": "monday_sla_orcamento_viu2", "policy": VERSION,
        "source_sha": source_sha, "files": {n: hashlib.sha256(b).hexdigest() for n, b in files.items()}}).encode()
    output = root / "runtime/viu2-sla-escopo-20260923-v1.zip"
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as zipped:
        for name, data in files.items():
            zipped.writestr(name, data)
    with ZipFile(output) as zipped:
        if zipped.testzip() or any(zipped.read(n) != b for n, b in files.items()):
            raise ValueError("ZIP divergente")
    print(json.dumps({"file": str(output), "rows": len(selected),
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest(), "cloud_modified": False}))


if __name__ == "__main__":
    main()
