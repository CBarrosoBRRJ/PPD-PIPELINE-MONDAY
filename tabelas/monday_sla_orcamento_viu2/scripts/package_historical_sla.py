"""Prepare a final-name historical load package; no cloud writes or KPI approval."""

import gzip
import hashlib
import json
import zipfile
from pathlib import Path

from historico_viu2.review_contract import validate


def main():
    root = Path("runtime/validation/viu2_review_export_20260922_v1")
    manifest = json.loads((root / "manifest.json").read_bytes())
    files = {}
    for name in ("review.ndjson.gz", "schema.json"):
        content = (root / name).read_bytes()
        if hashlib.sha256(content).hexdigest() != manifest["files"][name]["sha256"]:
            raise ValueError("Artefato divergente")
        files[name] = content
    rows = [json.loads(line) for line in gzip.decompress(files["review.ndjson.gz"]).splitlines()]
    validate(rows)
    scripts = Path(__file__).resolve().parent
    files["publish_historical_sla.py"] = (scripts / "publish_historical_sla.py").read_bytes()
    files["publish_history.py"] = (scripts.parents[1] / "monday_log_viu2/src/monday_log_viu2/publication.py").read_bytes()
    files["load_manifest.json"] = json.dumps({
        "authorization": "User explicitly requested the final table name before business review; no claim of automatic overnight validation.",
        "only_table": "gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento_viu2",
        "rows": len(rows), "final_name_load_authorized": True, "kpi_approved": False,
        "includes_globocorp": False, "scheduled": False,
        "files": {n: hashlib.sha256(b).hexdigest() for n, b in files.items()},
    }, indent=2).encode()
    output = Path("runtime/viu2-sla-bq-20260922-v1.zip")
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() or any(archive.read(n) != b for n, b in files.items()):
            raise ValueError("Pacote divergente apos releitura")
    print(json.dumps({"file": str(output), "rows": len(rows), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
