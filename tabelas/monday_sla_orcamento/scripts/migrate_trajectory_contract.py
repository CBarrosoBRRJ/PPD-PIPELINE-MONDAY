"""Explicit v4->v5 control migration, stopped writer, pinned base and generation CAS."""

import argparse
import json
import subprocess

import migrate_kpi_contract as migration


def configure():
    migration.OLD = {**migration.OLD, "contract": "sla-consolidado-consumo-v4"}
    migration.NEW = {**migration.OLD, "contract": "sla-consolidado-trajetoria-v5"}
    migration.FINGERPRINT = "3c3ee3cb5a92a96052687300f45efd287ff440f0620d169db4fd64aa961e8f78"


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
