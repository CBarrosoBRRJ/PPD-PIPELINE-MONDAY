import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "prepare_release", ROOT / "orquestracao/deploy/prepare_release.py"
)
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


def test_release_allowlist_and_hashes(tmp_path):
    import hashlib

    output = tmp_path / "release.zip"
    receipt = release.build_release(ROOT, output)
    with ZipFile(output) as archive:
        names = archive.namelist()
        assert all((item.external_attr >> 16) & 0o777 == 0o644 for item in archive.infolist())
        assert "Dockerfile" in names
        assert 'migrate_talent_contract.py' in names
        assert 'migrate_pricing_contract.py' in names
        assert not any(".env" in n or "runtime/" in n for n in names)
        assert "tabelas/monday_sla_orcamento/src/monday_sla_orcamento/consolidation.py" in names
        inventory = json.loads(archive.read("release-manifest.json"))
        assert len(inventory) == receipt["files"]
        for name, digest in inventory.items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
    with pytest.raises(FileExistsError):
        release.build_release(ROOT, output)


def test_image_defaults_to_plan_and_only_daily_product():
    from pipeline_monday.runner import plan

    docker = (ROOT / "orquestracao/deploy/Dockerfile").read_text()
    assert 'CMD ["plan", "--manifest", "/app/pipelines.json"]' in docker
    assert "USER pipeline" in docker
    assert "RUN chmod 0644 /app/pipelines.json" in docker
    document = json.loads((ROOT / "orquestracao/deploy/pipelines.json").read_text())
    assert [p["id"] for p in plan(document)] == ["monday_backlog_agenciamento_2026", "monday_talentos_exclusivos", "sla_orcamento", "monday_sla_orcamento"]
    assert next(p for p in document['products'] if p['id'] == 'sla_orcamento')['env_file'] == '.env'
