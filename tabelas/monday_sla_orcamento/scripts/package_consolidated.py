"""Package the initial load without credentials or cloud mutations."""

import hashlib
import json
import zipfile
from pathlib import Path


def main():
    source = Path("runtime/validation/consolidated_20260922_v3")
    scripts = Path(__file__).resolve().parent
    files = {n: (source / n).read_bytes() for n in (
        "manifest.json", "consolidated.ndjson.gz", "schema.json", "selected_identity.json.gz")}
    files["publish_consolidated.py"] = (scripts / "publish_consolidated.py").read_bytes()
    files["publish_history.py"] = (scripts.parents[1] / "monday_log_viu2/src/monday_log_viu2/publication.py").read_bytes()
    files["consolidation.py"] = (scripts.parent / "src/monday_sla_orcamento/consolidation.py").read_bytes()
    output = Path("runtime/monday-consolidado-bq-20260922-v3.zip")
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() or any(archive.read(n) != b for n, b in files.items()):
            raise ValueError("ZIP divergente")
    print(json.dumps({"file": str(output), "bytes": output.stat().st_size,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
