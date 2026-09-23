"""Create an exclusive, source-only build ZIP. Never reads environment or credentials."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


def release_files(root):
    fixed = {
        "migrate_analysis_contract.py": "tabelas/monday_sla_orcamento/scripts/migrate_analysis_contract.py",
        "migrate_estimates_contract.py": "tabelas/monday_sla_orcamento/scripts/migrate_estimates_contract.py",
        "migrate_trajectory_contract.py": "tabelas/monday_sla_orcamento/scripts/migrate_trajectory_contract.py",
        "migrate_consumption_contract.py": "tabelas/monday_sla_orcamento/scripts/migrate_consumption_contract.py",
        "migrate_kpi_contract.py": "tabelas/monday_sla_orcamento/scripts/migrate_kpi_contract.py",
        "compartilhado/pyproject.toml": "compartilhado/pyproject.toml",
        "Dockerfile": "orquestracao/deploy/Dockerfile",
        "orquestracao/deploy/pipelines.json": "orquestracao/deploy/pipelines.json",
        "orquestracao/pyproject.toml": "orquestracao/pyproject.toml",
        "tabelas/monday_sla_orcamento_globocorp/pyproject.toml": "tabelas/monday_sla_orcamento_globocorp/pyproject.toml",
        "tabelas/monday_sla_orcamento_viu2/pyproject.toml": "tabelas/monday_sla_orcamento_viu2/pyproject.toml",
        "tabelas/monday_log_viu2/pyproject.toml": "tabelas/monday_log_viu2/pyproject.toml",
        "tabelas/monday_sla_orcamento/pyproject.toml": "tabelas/monday_sla_orcamento/pyproject.toml",
    }
    root = root.resolve()
    selected = dict(fixed)
    for directory in ("compartilhado/src", "orquestracao/src", "tabelas/monday_sla_orcamento_globocorp/src", "tabelas/monday_sla_orcamento_viu2/src", "tabelas/monday_log_viu2/src", "tabelas/monday_sla_orcamento/src"):
        paths = list((root / directory).rglob("*.py"))
        if not paths:
            raise ValueError("Source package missing")
        for path in paths:
            relative = path.relative_to(root).as_posix()
            selected[relative] = relative
    for source in selected.values():
        path = root / source
        if (not path.is_file() or path.is_symlink()
                or any(p.is_symlink() for p in path.parents if p != root)
                or not path.resolve().is_relative_to(root)):
            raise ValueError("Invalid release input")
    return {name: root / source for name, source in sorted(selected.items())}


def build_release(root, output):
    files = release_files(root)
    # Read and hash all selected inputs before creating the output.
    contents = {name: path.read_bytes() for name, path in files.items()}
    inventory = {name: hashlib.sha256(data).hexdigest() for name, data in contents.items()}
    with output.open("xb") as handle, ZipFile(handle, "w", ZIP_DEFLATED) as archive:
        for name, data in contents.items():
            write_public_source(archive, name, data)
        write_public_source(archive, "release-manifest.json", json.dumps(inventory, indent=2))
    return {"files": len(contents), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}


def write_public_source(archive, name, data):
    # ZIP defaults to 0600; Linux preserves that on extraction. Inputs are code only.
    entry = ZipInfo(name)
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    entry.compress_type = ZIP_DEFLATED
    archive.writestr(entry, data)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    print(json.dumps(build_release(root, args.output)))


if __name__ == "__main__":
    main()
