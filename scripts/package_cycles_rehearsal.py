"""Pacote allowlist para ensaio Cloud Shell; nao e release de producao."""
import hashlib
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = ['compartilhado', 'orquestracao', 'tabelas/monday_sla_orcamento_globocorp',
            'tabelas/monday_sla_orcamento_viu2', 'tabelas/monday_log_viu2',
            'tabelas/monday_sla_orcamento', 'tabelas/monday_backlog_agenciamento_2026',
            'tabelas/monday_talentos_exclusivos']


def main():
    files = [ROOT / 'scripts/rehearse_live_cycles_cloudshell.py']
    for package in PACKAGES:
        files.append(ROOT / package / 'pyproject.toml')
        files.extend(p for p in (ROOT / package / 'src').rglob('*')
                     if p.is_file() and p.suffix in {'.py', '.json'} and '__pycache__' not in p.parts)
    target = ROOT / 'runtime/pipeline-monday-ciclos-ensaio-20260925.zip'
    manifest = {}
    with ZipFile(target, 'x', ZIP_DEFLATED) as archive:
        for path in sorted(files):
            name = path.relative_to(ROOT).as_posix()
            raw = path.read_bytes()
            manifest[name] = hashlib.sha256(raw).hexdigest()
            archive.writestr(name, raw)
        archive.writestr('manifest.json', json.dumps(manifest, indent=2))
    with ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError('ZIP corrompido')
        for name, sha in manifest.items():
            if hashlib.sha256(archive.read(name)).hexdigest() != sha:
                raise ValueError('Manifesto divergente')
    print(json.dumps({'file': str(target), 'files': len(files),
                      'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
