"""Explicit v5->v6 control migration with pinned base and stopped-writer CAS guards."""

import argparse
import json
import subprocess

import migrate_kpi_contract as migration


def configure():
    migration.OLD = {**migration.OLD, "contract": "sla-consolidado-trajetoria-v5"}
    migration.NEW = {**migration.OLD, "contract": "sla-consolidado-estimativas-v6"}
    migration.FINGERPRINT = "b676c79b17237437c193bb28fde297ad9452b6ab34250a5bf9670c30ee53a895"


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
