"""Guarded v8 -> v9 migration, reusing the reviewed CAS engine in an isolated module."""

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path


def engine():
    spec = importlib.util.spec_from_file_location(
        'talent_migration_engine', Path(__file__).with_name('migrate_pricing_contract.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OLD = {**module.OLD, 'contract': 'sla-consolidado-precificacao-v8'}
    module.NEW = {**module.OLD, 'contract': 'sla-consolidado-talentos-v9'}
    return module


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('plan', 'apply'))
    parser.add_argument('--expected-generation')
    parser.add_argument('--expected-fingerprint')
    parser.add_argument('--expected-image')
    args = parser.parse_args()
    try:
        print(json.dumps(engine().run(
            apply=args.mode == 'apply', generation=args.expected_generation,
            fingerprint=args.expected_fingerprint, image=args.expected_image), indent=2))
    except (ValueError, subprocess.CalledProcessError) as error:
        print(json.dumps({'status': 'migration_not_confirmed', 'error_type': type(error).__name__}))
        if isinstance(error, ValueError):
            print(str(error))
        raise SystemExit(1) from None
