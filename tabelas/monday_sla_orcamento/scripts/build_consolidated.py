"""Build the initial unified evidence table from verified, published source snapshots."""

import gzip
import hashlib
import json
from pathlib import Path

from monday_sla_orcamento.consolidation import VERSION, build, schema, validate


def main():
    sources = {
        "viu2": (Path("runtime/validation/viu2_review_export_20260922_v1/review.ndjson.gz"),
                 "e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532"),
        "globocorp": (Path("C:/Users/CCMB/Downloads/globocorp-para-consolidacao.json.gz"),
                      "3f3d07cef374f11b3b6811364e62099ca81c4a517026dbdefbc7798f29ec83e7"),
        "identity": (Path("runtime/validation/selected_identity_20260922_v1/selected_identity.json.gz"),
                     "486845629229aaa881c38ab87d58cec49811f539642d413d9aa29f07569399eb"),
    }
    raw = {}
    for name, (path, sha) in sources.items():
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != sha:
            raise ValueError("Fonte divergente: " + name)
        raw[name] = content
    old = [json.loads(line) for line in gzip.decompress(raw["viu2"]).splitlines()]
    new = json.loads(gzip.decompress(raw["globocorp"]))
    if new["table"] != "gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento_globocorp":
        raise ValueError("Tabela fonte divergente")
    if len(new["rows"]) != int(new["metadata"]["numRows"]):
        raise ValueError("Fonte truncada")
    rows, report = build(old, new["rows"], json.loads(gzip.decompress(raw["identity"])))
    output = Path("runtime/validation/consolidated_20260922_v3")
    output.mkdir(exist_ok=False)
    data = gzip.compress(b"".join((json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
                                 for r in rows), mtime=0)
    restored = [json.loads(line) for line in gzip.decompress(data).splitlines()]
    validate(restored)
    if rows != restored:
        raise ValueError("Serializacao divergente")
    artifacts = {"consolidated.ndjson.gz": data, "schema.json": json.dumps(schema(), indent=2).encode(),
                 "selected_identity.json.gz": raw["identity"]}
    manifest = {"contract": VERSION, "destination": "monday_sla_orcamento", **report,
                "source_hashes": {k: v[1] for k, v in sources.items()},
                "expected_source_modified": {"monday_sla_orcamento_viu2": "1790127403215",
                                             "monday_sla_orcamento_globocorp": new["metadata"]["lastModifiedTime"]},
                "files": {name: {"sha256": hashlib.sha256(b).hexdigest(), "bytes": len(b)} for name, b in artifacts.items()}}
    for name, content in artifacts.items():
        with (output / name).open("xb") as stream:
            stream.write(content)
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
