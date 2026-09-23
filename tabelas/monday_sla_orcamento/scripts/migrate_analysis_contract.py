"""Explicit v6->v7 control migration; frozen base, stopped writer and CAS."""

import argparse
import json
import subprocess

import migrate_kpi_contract as migration


def configure():
    migration.OLD = {**migration.OLD, "contract": "sla-consolidado-estimativas-v6"}
    migration.NEW = {**migration.OLD, "contract": "sla-consolidado-analise-v7"}
    migration.FINGERPRINT = "daba7914c4ccbcf8f6d7d60c1b97e2bce742a62a86b379690a89b48cca069bef"


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
