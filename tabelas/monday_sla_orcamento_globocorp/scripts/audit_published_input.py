"""Read-only local audit of downloaded state and BigQuery JSON export."""

import argparse
import gzip
import hashlib
import json
from collections import Counter
from datetime import date, datetime
from pathlib import Path

from monday_comum.escopo_sla import (
    coluna_input,
    ler_input,
    motivos_exclusao,
    motivos_input,
    normalizar_titulo,
)

from sls_orcamento_ppd.db.checkpoint import decode
from sls_orcamento_ppd.models.bq_consumption import FIELDS, digest, validate_public


def checked(path, sha):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        raise ValueError("Arquivo divergente do checksum informado")
    return data


def normalize_export(blob):
    rows = []
    for line in gzip.decompress(blob).splitlines():
        raw = json.loads(line)
        row = {}
        fields = dict(field.split(":") for field in FIELDS.split())
        if set(raw) - fields.keys():
            raise ValueError("Exportacao contem campos inesperados")
        for key, kind in fields.items():
            value = raw.get(key)
            if value is not None:
                if kind in {"id", "int"}:
                    value = int(value)
                elif kind == "num":
                    value = float(value)
                elif kind in {"time", "localtime"}:
                    value = datetime.fromisoformat(value.replace(" UTC", "+00:00").replace("Z", "+00:00"))
                elif kind == "date":
                    value = date.fromisoformat(value)
            row[key] = value
        rows.append(row)
    validate_public(rows, 18429499488)
    return rows


def audit(state, rows):
    at = max(r["registrado_em"] for r in state["meta_gold_rule_snapshot"])
    boards = [r for r in state["bronze_monday_board_schema_raw"]
              if r["board_id"] == 18429499488 and r["snapshot_at"] <= at]
    board = max(boards, key=lambda r: r["snapshot_at"])["raw_data"]
    column = coluna_input(json.loads(board) if isinstance(board, str) else board)
    snapshots = {}
    for row in state["bronze_monday_item_snapshot_raw"]:
        key = (row["board_id"], row["item_id"], row["snapshot_at"])
        if key in snapshots:
            raise ValueError("Cadastro duplicado")
        snapshots[key] = row
    projects = {}
    for row in rows:
        key = (row["board_id"], row["item_id"])
        ref = row["cadastro_referencia_utc"]
        if key in projects and projects[key] != ref:
            raise ValueError("Referencias de cadastro divergentes")
        projects[key] = ref
    counts = Counter(missing_snapshot=0, unverified_input=0, denied_input=0,
                     denied_title=0, verified_blank_allowed=0)
    for key, ref in projects.items():
        snapshot = snapshots.get((*key, ref))
        if snapshot is None:
            counts["missing_snapshot"] += 1
            continue
        try:
            value = ler_input(column, snapshot["raw_data"])
        except ValueError:
            counts["unverified_input"] += 1
            continue
        counts["denied_input"] += bool(motivos_input(value))
        counts["denied_title"] += bool(motivos_exclusao(snapshot["item_name"]))
        counts["verified_blank_allowed"] += not normalizar_titulo(value)
    result = {"rows": len(rows), "projects": len(projects), "counts": dict(counts),
              "cloud_modified": False, "kpi_approved": False}
    if any(counts[k] for k in ("missing_snapshot", "unverified_input", "denied_input", "denied_title")):
        raise ValueError("Auditoria de escopo reprovada; publicacao nao autorizada")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("state", "export", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    for name in ("state-sha", "export-sha", "gold-hash"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    state = decode(checked(args.state, args.state_sha))
    rows = normalize_export(checked(args.export, args.export_sha))
    if digest(rows) != args.gold_hash:
        raise ValueError("Exportacao nao corresponde ao hash da publicacao")
    result = audit(state, rows)
    result.update(state_sha256=args.state_sha, export_sha256=args.export_sha,
                  publication_hash_verified=True, gold_hash=args.gold_hash)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
