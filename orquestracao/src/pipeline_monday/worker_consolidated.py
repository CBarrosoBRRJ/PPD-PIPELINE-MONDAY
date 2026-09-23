"""Frozen viu2 + verified current globocorp; only consolidated destination is written."""

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from google.cloud import bigquery
from historico_viu2.eligibility import frozen_inputs
from monday_comum.escopo_sla import VERSION as SCOPE_VERSION
from monday_sla_orcamento.consolidation import build, timestamp
from monday_sla_orcamento.publication import (
    BUCKET,
    DATASET,
    HISTORY_SHA,
    INITIAL_PREFIX,
    INITIAL_SHA,
    MAP_SHA,
    PROJECT,
    SOURCE,
    ConsolidatedStore,
    checked_object,
)
from sls_orcamento_ppd.config import load_settings
from sls_orcamento_ppd.db import get_store
from sls_orcamento_ppd.db.gcs import ObjectStore
from sls_orcamento_ppd.rules.cutoff import closed_day_cut


def ensure_current(rows, scheduled, timezone):
    cut = closed_day_cut(scheduled, timezone)
    if not rows or {timestamp(r["corte_utc"]) for r in rows} != {cut}:
        raise ValueError("Consolidado: fonte nao corresponde ao fechamento solicitado")
    return cut


def execute(settings, scheduled, *, recover_only=False):
    if (settings.bq_project != PROJECT or settings.bq_dataset != DATASET
            or settings.bq_table != "monday_sla_orcamento_globocorp"
            or settings.gcs_bucket != BUCKET or settings.gcs_prefix != "sla_orcamento"
            or settings.bq_location.upper() != "US"
            or settings.monday_board_id != 18429499488
            or settings.monday_status_column_id != "status_19"
            or settings.preferred_timezone != "America/Sao_Paulo"):
        raise ValueError("Consolidado: configuracao fora do escopo autorizado")
    source = get_store(settings)
    objects = ObjectStore(SimpleNamespace(bq_project=PROJECT, gcs_bucket=BUCKET,
                                          gcs_prefix="consolidado/diario"))
    publisher = ConsolidatedStore(source.client, objects,
                                 timeout=settings.bq_job_timeout_seconds)
    # Always acquire source first. Keeps globocorp writer out through publication.
    with source.lock(), objects.lock():
        publisher.bootstrap([json.loads(line) for line in checked_object(
            objects.bucket, INITIAL_PREFIX + "consolidated.ndjson.gz", INITIAL_SHA).splitlines()])
        publisher.recover()  # Resolve an older uncertain load before admitting a candidate.
        if recover_only:
            active = publisher.control()[0]["active"]
            publisher.verify(active)
            return {"status": "success", "publication_verified": True,
                    "gold_rows": active["rows"], "gold_cut_utc": active["cut"]}
        connection = source.check_connection()
        if connection["pending"] or not connection["published"]:
            raise ValueError("Consolidado: origem com publicacao pendente")
        before = source.client.get_table(SOURCE)
        config = bigquery.QueryJobConfig(use_query_cache=False, maximum_bytes_billed=1073741824)
        query = source.client.query("SELECT TO_JSON_STRING(t) AS registro FROM `" + SOURCE + "` AS t",
                                    location="US", job_config=config)
        new = [json.loads(r["registro"]) for r in query.result(timeout=settings.bq_job_timeout_seconds)]
        ensure_current(new, scheduled, settings.preferred_timezone)
        versions = {r["versao_regras"] for r in new}
        rule_snapshots = source.read("meta_gold_rule_snapshot", settings.monday_board_id)
        confirmed = {r["versao_regras"] for r in rule_snapshots
                     if r["conteudo"].get("title_scope_version") == SCOPE_VERSION}
        if not versions <= confirmed:
            raise ValueError("Consolidado: globocorp ainda nao publicou as regras de escopo atuais")
        old = [json.loads(line) for line in checked_object(
            objects.bucket, "historico_viu2/sla_publicado/" + HISTORY_SHA + "/review.ndjson.gz",
            HISTORY_SHA).splitlines()]
        mapping = json.loads(checked_object(objects.bucket, INITIAL_PREFIX + "selected_identity.json.gz", MAP_SHA))
        prefix = os.environ.get("VIU2_ARCHIVE_PREFIX", "").strip("/")
        if not prefix.startswith("historico_viu2/") or ".." in prefix:
            raise ValueError("Consolidado: informe VIU2_ARCHIVE_PREFIX conferido no bucket")
        def read_context(name):
            blob = objects.bucket.get_blob(prefix + "/" + name)
            if blob is None:
                raise ValueError("Consolidado: contexto viu2 ausente")
            return blob.download_as_bytes(if_generation_match=int(blob.generation))
        rows, report = build(old, new, mapping, old_inputs=frozen_inputs(read_context))
        # Detect external edits as well as conflicting cooperative pipeline writes.
        source.check_connection()
        if source.client.get_table(SOURCE).etag != before.etag:
            raise ValueError("Consolidado: fonte mudou durante a leitura")
        evidence = {"table": SOURCE, "etag": before.etag, "history_sha": HISTORY_SHA,
                    "map_sha": MAP_SHA, "scheduled_for": scheduled.isoformat()}
        return publisher.publish(rows, report, evidence)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--scheduled-for", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--recover-only", action="store_true")
    args = parser.parse_args()
    try:
        scheduled = datetime.fromisoformat(args.scheduled_for)
        if scheduled.utcoffset() is None:
            raise ValueError("Referencia sem fuso")
        if args.env_file != "globocorp-runtime":
            raise ValueError("Consolidado: seletor de configuracao invalido")
        # Explicit source runtime binding, not a second secret file. Output settings
        # are fixed separately; BQ_TABLE is never changed to the consolidated target.
        receipt = execute(load_settings(".env"), scheduled, recover_only=args.recover_only)
        with Path(args.result).open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle)
        print(json.dumps({"event": "consolidated_publication_confirmed", **receipt}), flush=True)
    except Exception as error:
        print(json.dumps({"event": "consolidated_worker_failed", "error_type": type(error).__name__}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
