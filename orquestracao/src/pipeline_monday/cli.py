import argparse
import json
from pathlib import Path

from .runner import plan, run


def maintenance(document, args):
    products = plan(document)
    if len(products) != 1 or products[0]["runner"] != "sla_orcamento":
        raise ValueError("Manutenção exige manifesto exclusivo do SLA")
    applying = args.command == "rename-sla-apply"
    if applying and (not args.writers_stopped or not args.expected_generation
                     or args.expected_generation <= 0):
        raise ValueError("Aplicação exige escritores parados e geração esperada")
    from sls_orcamento_ppd.config import load_settings
    from sls_orcamento_ppd.db import get_store
    from sls_orcamento_ppd.migration.rename_destination import rebind_destination

    settings = load_settings(products[0]["env_file"])
    result = rebind_destination(
        get_store(settings), apply=applying, writers_stopped=args.writers_stopped,
        expected_generation=args.expected_generation,
    )
    return {"event": "sla_destination_migration", **result}


def main():
    parser = argparse.ArgumentParser(description="Pipeline Monday — execução sequencial por produto")
    parser.add_argument("command", choices=["plan", "snapshot-check", "daily", "cycles-plan", "initialize-destinations", "initialize-cycles", "rename-sla-plan", "rename-sla-apply"])
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--expected-generation", type=int)
    parser.add_argument("--writers-stopped", action="store_true")
    args = parser.parse_args()
    try:
        document = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        if args.command == 'cycles-plan':
            if args.writers_stopped or args.expected_generation is not None:
                raise ValueError('Ciclos: plano nao recebe opcoes de migracao')
            plan(document)
            from datetime import UTC, datetime

            from sls_orcamento_ppd.config import load_settings

            from .worker_consolidated import execute

            try:
                receipt = execute(load_settings('.env'), datetime.now(UTC), cycles_bundle_check=True)
            except Exception as error:
                print(json.dumps({'event': 'cycles_bundle_plan_failed',
                                  'error_type': type(error).__name__}), flush=True)
                raise SystemExit(1) from None
            print(json.dumps({'event': 'cycles_bundle_plan', **receipt}), flush=True)
            return
        if args.command in {'initialize-destinations', 'initialize-cycles'}:
            if not args.writers_stopped or args.expected_generation is not None:
                raise ValueError('Destinos: declarar escritores parados; nao usa geracao manual')
            plan(document)
            from datetime import UTC, datetime

            from sls_orcamento_ppd.config import load_settings

            from .worker_consolidated import execute

            try:
                option = 'initialize_cycles' if args.command == 'initialize-cycles' else 'initialize_destinations'
                receipt = execute(load_settings('.env'), datetime.now(UTC), **{option: True})
                print(json.dumps({'event': 'destinations_initialized', **receipt}), flush=True)
            except Exception as error:
                print(json.dumps({'event': 'destinations_initialization_failed',
                                  'error_type': type(error).__name__}), flush=True)
                raise SystemExit(1) from None
            return
        if args.command.startswith("rename-sla-"):
            try:
                print(json.dumps(maintenance(document, args)), flush=True)
            except Exception as error:
                print(json.dumps({"event": "sla_destination_migration_failed",
                                  "error_type": type(error).__name__}), flush=True)
                raise SystemExit(1) from None
            return
        if args.writers_stopped or args.expected_generation is not None:
            raise ValueError("Opções de migração não se aplicam à rotina diária")
        if args.command == "plan":
            print(json.dumps({"mode": "plan_only", "order": [p["id"] for p in plan(document)]}))
            return
        if args.command == 'snapshot-check':
            plan(document)
            from .preflight import run as preflight
            result = preflight()
            print(json.dumps(result), flush=True)
            if result['status'] != 'success':
                raise SystemExit(1)
            return
        result = run(document)
        print(json.dumps(result), flush=True)
        from .alerts import notify
        notification = notify(result)
        if notification != 'not_needed':
            print(json.dumps({'event': 'pipeline_alert', 'delivery': notification,
                              'severity': 'ERROR' if notification != 'sent' else 'INFO'}), flush=True)
        if result["status"] in {"failed", "partial"}:
            raise SystemExit(1)
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"event": "orchestration_error", "reason": "invalid_configuration"}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
