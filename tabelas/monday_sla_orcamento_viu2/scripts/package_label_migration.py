"""Package fixed reviewed label migration, excluding raw state and credentials."""

import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    root = Path(__file__).resolve().parents[3]
    preflight = root / "runtime/viu2-rotulos-preflight-20260923-v1.zip"
    if hashlib.sha256(preflight.read_bytes()).hexdigest() != "93cdcbca4c4c59e23768a54979c136748ab9ea0719160a2ca01272f490899e9c":
        raise ValueError("Plano divergente")
    with ZipFile(preflight) as archive:
        files = {name: archive.read(name) for name in
                 ("before.ndjson.gz", "after.ndjson.gz", "schema.json", "manifest.json", "plan_label_migration.py")}
    scripts = Path(__file__).parent
    for name in ("migrate_labels.py", "migrate_scope.py"):
        files[name] = (scripts / name).read_bytes()
    files["publish_history.py"] = (root / "tabelas/monday_log_viu2/src/monday_log_viu2/publication.py").read_bytes()
    files["filtered.ndjson.gz"] = files["after.ndjson.gz"]
    files["coordinator_source.ndjson.gz"] = (root / "runtime/validation/viu2_review_labels_v2/coordinator_source.ndjson.gz").read_bytes()
    if hashlib.sha256(files["coordinator_source.ndjson.gz"]).hexdigest() != "d0aab3fdb25cb1f3746ee0f1c6db37c419e255034b6ce9786ff3e6d84e78af1e":
        raise ValueError("Fonte divergente")
    files["migration-inventory.json"] = json.dumps({name: hashlib.sha256(data).hexdigest()
                                                    for name, data in files.items()}, indent=2).encode()
    out = root / "runtime/viu2-rotulos-migracao-20260923-v2.zip"
    with ZipFile(out, "x", compression=ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    with ZipFile(out) as archive:
        if archive.testzip() or any(archive.read(n) != b for n, b in files.items()):
            raise ValueError("Pacote nao reconciliado")
    print(json.dumps({"file": str(out), "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
                      "cloud_modified": False}))


if __name__ == "__main__":
    main()
