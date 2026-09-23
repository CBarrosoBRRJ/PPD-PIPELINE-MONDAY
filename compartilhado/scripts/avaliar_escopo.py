"""Local impact analysis of fixed snapshots. No cloud writes or excluded-item list."""

import gzip
import hashlib
import json
from pathlib import Path

from historico_viu2.eligibility import frozen_inputs
from monday_comum.escopo_sla import VERSION, coluna_input, filtrar_projetos, ler_input
from monday_sla_orcamento.consolidation import build


def checked(path, sha):
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != sha:
        raise ValueError("Impacto: fonte divergente")
    return gzip.decompress(content)


def sources(root):
    archive = root / "runtime/archives/viu2_18393336134_20260921"
    old_inputs = frozen_inputs(lambda name: (archive / name).read_bytes())
    old = [json.loads(line) for line in checked(
        root / "runtime/validation/viu2_review_export_20260922_v1/review.ndjson.gz",
        "e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532").splitlines()]
    new_context = json.loads(checked(root / "runtime/validation/project_matching_20260922_v3/globocorp_context.json.gz",
                                    "84238538b3b80a794cd68223b1b3f819d13b810d991c0cd08002ac83326e8575"))
    new_column = coluna_input(new_context["board"])
    new_inputs = {(18429499488, int(item["id"])): ler_input(new_column, item) for item in new_context["items"]}
    new = json.loads(checked(Path("C:/Users/CCMB/Downloads/globocorp-para-consolidacao.json.gz"),
                            "3f3d07cef374f11b3b6811364e62099ca81c4a517026dbdefbc7798f29ec83e7"))["rows"]
    mapping = json.loads(checked(root / "runtime/validation/selected_identity_20260922_v1/selected_identity.json.gz",
                                "486845629229aaa881c38ab87d58cec49811f539642d413d9aa29f07569399eb"))
    return old, new, mapping, old_inputs, new_inputs


def main():
    root = Path(__file__).resolve().parents[2]
    old, new, mapping, old_inputs, new_inputs = sources(root)
    selected_old = filtrar_projetos(old, old_inputs)
    selected_new = filtrar_projetos(new, new_inputs)
    # If a native project was explicitly excluded on either side, exclude its pair.
    excluded_old = {r["item_id"] for r in old} - {r["item_id"] for r in selected_old}
    excluded_new = {r["item_id"] for r in new} - {r["item_id"] for r in selected_new}
    selected_map = {**mapping, "rows": [p for p in mapping["rows"]
                    if int(p["viu2_item_id"]) not in excluded_old and int(p["globocorp_item_id"]) not in excluded_new]}
    consolidated, report = build(selected_old, selected_new, selected_map)
    runtime_rows, _ = build(old, selected_new, mapping, old_inputs=old_inputs)
    if runtime_rows != consolidated:
        raise ValueError("Impacto: recorte local diverge do caminho diario")
    summary = {"policy": VERSION, "cloud_modified": False,
               "snapshot_only_not_current_cloud": True,
               "viu2": {"before": len(old), "after": len(selected_old), "excluded_projects": len(excluded_old),
                        "projects_without_input_context": len({r["item_id"] for r in old if (r["board_id"], r["item_id"]) not in old_inputs})},
               "globocorp": {"before": len(new), "after": len(selected_new), "excluded_projects": len(excluded_new),
                             "projects_without_input_context": len({r["item_id"] for r in new
                                 if (r["board_id"], r["item_id"]) not in new_inputs})},
               "consolidated": {"after": len(consolidated), "projects": report["projects"]}}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
