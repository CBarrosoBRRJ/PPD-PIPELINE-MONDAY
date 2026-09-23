"""Explicit v3->v4 control migration; same stopped-writer and CAS guards as v8."""

import argparse
import json
import subprocess

import migrate_kpi_contract as migration


def configure():
    migration.OLD = {**migration.OLD, "contract": "sla-consolidado-etapa-v3"}
    migration.NEW = {**migration.OLD, "contract": "sla-consolidado-consumo-v4"}
    migration.FINGERPRINT = "89d4c1281e616533c16ba960bf1dfeee0f81432bb2fcf441e1a6b010303a1135"


if __name__ == "__main__":
    configure()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "apply"))
    parser.add_argument("--expected-generation")
    parser.add_argument("--expected-image")
    args = parser.parse_args()
    try:
        print(json.dumps(migration.run(apply=args.mode == "apply", expected_generation=args.expected_generation,
                                       image=args.expected_image), indent=2))
    except (ValueError, subprocess.CalledProcessError) as error:
        print(json.dumps({"status": "migration_not_confirmed", "error_type": type(error).__name__}))
        if isinstance(error, ValueError):
            print(str(error))
        raise SystemExit(1) from None
