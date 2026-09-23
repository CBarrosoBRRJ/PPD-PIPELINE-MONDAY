import importlib.util
import sys
from pathlib import Path


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v4_migration_uses_v3_receipt_and_shared_guards(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    base = load("isolated_migration", scripts / "migrate_kpi_contract.py")
    monkeypatch.setitem(sys.modules, "migrate_kpi_contract", base)
    wrapper = load("consumption_migration", scripts / "migrate_consumption_contract.py")
    wrapper.configure()
    assert base.OLD["contract"] == "sla-consolidado-etapa-v3"
    assert base.NEW["contract"] == "sla-consolidado-consumo-v4"
    assert base.FINGERPRINT == "89d4c1281e616533c16ba960bf1dfeee0f81432bb2fcf441e1a6b010303a1135"
    control = {"identity": base.OLD, "pending": None, "active": {"fingerprint": base.FINGERPRINT, "rows": 9648}}
    monkeypatch.setattr(base, "read_control", lambda: (control, "123"))
    assert base.run()["status"] == "plan_no_writes"


def test_v5_migration_uses_v4_receipt_and_shared_guards(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    base = load("isolated_trajectory_migration", scripts / "migrate_kpi_contract.py")
    monkeypatch.setitem(sys.modules, "migrate_kpi_contract", base)
    wrapper = load("trajectory_migration", scripts / "migrate_trajectory_contract.py")
    wrapper.configure()
    assert base.OLD["contract"] == "sla-consolidado-consumo-v4"
    assert base.NEW["contract"] == "sla-consolidado-trajetoria-v5"
    assert base.FINGERPRINT == "3c3ee3cb5a92a96052687300f45efd287ff440f0620d169db4fd64aa961e8f78"
    control = {"identity": base.OLD, "pending": None, "active": {"fingerprint": base.FINGERPRINT, "rows": 9648}}
    monkeypatch.setattr(base, "read_control", lambda: (control, "123"))
    assert base.run()["status"] == "plan_no_writes"


def test_v6_migration_uses_v5_receipt_and_shared_guards(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    base = load("isolated_estimates_migration", scripts / "migrate_kpi_contract.py")
    monkeypatch.setitem(sys.modules, "migrate_kpi_contract", base)
    wrapper = load("estimates_migration", scripts / "migrate_estimates_contract.py")
    wrapper.configure()
    assert base.OLD["contract"] == "sla-consolidado-trajetoria-v5"
    assert base.NEW["contract"] == "sla-consolidado-estimativas-v6"
    assert base.FINGERPRINT == "b676c79b17237437c193bb28fde297ad9452b6ab34250a5bf9670c30ee53a895"
    control = {"identity": base.OLD, "pending": None, "active": {"fingerprint": base.FINGERPRINT, "rows": 9648}}
    monkeypatch.setattr(base, "read_control", lambda: (control, "123"))
    assert base.run()["status"] == "plan_no_writes"


def test_v7_migration_uses_v6_receipt_and_shared_guards(monkeypatch):
    scripts = Path(__file__).parents[1] / "scripts"
    base = load("isolated_analysis_migration", scripts / "migrate_kpi_contract.py")
    monkeypatch.setitem(sys.modules, "migrate_kpi_contract", base)
    wrapper = load("analysis_migration", scripts / "migrate_analysis_contract.py")
    wrapper.configure()
    assert base.OLD["contract"] == "sla-consolidado-estimativas-v6"
    assert base.NEW["contract"] == "sla-consolidado-analise-v7"
    assert base.FINGERPRINT == "daba7914c4ccbcf8f6d7d60c1b97e2bce742a62a86b379690a89b48cca069bef"
    control = {"identity": base.OLD, "pending": None, "active": {"fingerprint": base.FINGERPRINT, "rows": 9648}}
    monkeypatch.setattr(base, "read_control", lambda: (control, "123"))
    assert base.run()["status"] == "plan_no_writes"
