"""Adapter for the existing SLA product. No new table names or implicit migration."""

import argparse
import json
from datetime import datetime
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--scheduled-for", required=True)
    parser.add_argument("--result", required=True)
    args = parser.parse_args()
    try:
        # Imports stay in the child so large product dependencies leave with it.
        from sls_orcamento_ppd.config import load_settings
        from sls_orcamento_ppd.pipelines.runner import run
        from sls_orcamento_ppd.rules.cutoff import closed_day_cut
        from sls_orcamento_ppd.services.gold import validate_gold
        from sls_orcamento_ppd.services.state import watermark

        from sls_orcamento_ppd.db import get_store

        settings = load_settings(args.env_file)
        scheduled = datetime.fromisoformat(args.scheduled_for)
        if scheduled.utcoffset() is None:
            raise ValueError("Referência sem fuso")
        report = run(settings, "daily", scheduled_for=scheduled)
        receipt = {k: report[k] for k in ("status", "run_id", "gold_rows", "gold_projects", "gold_cut_utc") if k in report}
        receipt["publication_verified"] = False
        if report["status"] in {"success", "skipped"}:
            store = get_store(settings)
            with store.lock():
                connection = store.check_connection()
                if connection["pending"] or not connection["published"]:
                    raise ValueError("Publicação não reconciliada")
                names = ["gold_projeto_status", "quarentena_projeto", "fct_item_status_interval", "data_quality_issue", "etl_watermark"]
                payload = store.read_many(names, settings.monday_board_id)
                previous = watermark(payload["etl_watermark"], settings.pipeline_name)
                if not previous or not payload["fct_item_status_interval"]:
                    raise ValueError("Estado sem histórico reconciliável")
                if closed_day_cut(previous["last_run_utc"], settings.preferred_timezone) != closed_day_cut(scheduled, settings.preferred_timezone):
                    raise ValueError("Publicação não corresponde ao fechamento solicitado")
                validate_gold(payload, cutoff=closed_day_cut(previous["last_run_utc"], settings.preferred_timezone))
            receipt["publication_verified"] = True
            receipt["gold_cut_utc"] = closed_day_cut(scheduled, settings.preferred_timezone).isoformat()
        with Path(args.result).open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle)
    except Exception as error:
        print(json.dumps({"event": "product_worker_failed", "error_type": type(error).__name__}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
