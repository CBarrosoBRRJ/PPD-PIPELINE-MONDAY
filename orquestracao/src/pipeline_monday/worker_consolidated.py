"""Frozen viu2 + verified current globocorp; only consolidated destination is written."""

import argparse
import hashlib
import json
import os
from collections import Counter
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from google.cloud import bigquery
from historico_viu2.eligibility import frozen_inputs
from monday_backlog_agenciamento_2026 import SPEC as BACKLOG_SPEC
from monday_comum.escopo_sla import VERSION as SCOPE_VERSION
from monday_comum.snapshot_publication import SnapshotStore
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


def execute(settings, scheduled, *, recover_only=False, initialize_destinations=False,
            cycles_check=False, initialize_cycles=False, cycles_bundle_check=False):
    cycles_check = cycles_check or cycles_bundle_check
    if cycles_check and (recover_only or initialize_destinations or initialize_cycles):
        raise ValueError('Ciclos: ensaio nao permite escrita/recuperacao')
    if initialize_cycles and (initialize_destinations or recover_only):
        raise ValueError('Ciclos: opcoes incompativeis')
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
    context_objects = ObjectStore(SimpleNamespace(bq_project=PROJECT, gcs_bucket=BUCKET,
                                                  gcs_prefix='snapshots/' + BACKLOG_SPEC['table']))
    context_store = SnapshotStore(source.client, context_objects, BACKLOG_SPEC)
    # Always acquire source first. Keeps globocorp writer out through publication.
    with (nullcontext() if cycles_check else source.lock()), \
            (nullcontext() if cycles_check else objects.lock()), \
            (nullcontext() if cycles_check else context_objects.lock()):
        from monday_sla_orcamento.cycle_publication import CONTROL as CYCLE_CONTROL
        from monday_sla_orcamento.cycle_publication import CycleStore
        from monday_sla_orcamento.destination_publication import CONTROL, DestinationStore
        from monday_sla_orcamento.destinations import build as split_destinations

        destinations = DestinationStore(source.client, objects, settings.bq_job_timeout_seconds)
        cycles_active = objects.get(CYCLE_CONTROL)[0] is not None
        if initialize_cycles:
            CycleStore(source.client, objects, settings.bq_job_timeout_seconds).initialize()
            return {'status': 'cycles_initialized', 'publication_verified': False,
                    'daily_rebuild_required': True}
        if cycles_active:
            if initialize_destinations:
                raise ValueError('Ciclos: retorno ao inicializador legado proibido')
            destinations = CycleStore(source.client, objects, settings.bq_job_timeout_seconds)
            from monday_sla_orcamento.cycle_destinations import build as split_destinations
        if initialize_destinations:
            if recover_only:
                raise ValueError('Destinos: opcoes incompatíveis')
            publisher.recover()
            destinations.initialize(publisher)
            return {'status': 'initialized', 'publication_verified': False,
                    'daily_rebuild_required': True}
        bundle_active = cycles_active or objects.get(CONTROL)[0] is not None
        if bundle_active:
            if cycles_check:
                read_control = destinations.control()
                if read_control[0]['pending'] or read_control[0]['initializing']:
                    raise ValueError('Ciclos: destinos em publicacao')
            else:
                destinations.recover()
            if recover_only:
                descriptor = destinations.control()[0]['active']
                if descriptor is None:
                    raise ValueError('Destinos: primeira publicacao pendente')
                destinations.verify(descriptor)
                return {'status': 'success', 'publication_verified': True,
                        'gold_rows': descriptor['tables']['monday_sla_orcamento']['rows'],
                        'gold_cut_utc': descriptor['cut']}
        if not cycles_check and not cycles_active:
            publisher.bootstrap([json.loads(line) for line in checked_object(
                objects.bucket, INITIAL_PREFIX + "consolidated.ndjson.gz", INITIAL_SHA).splitlines()])
        elif not bundle_active:
            raise ValueError('Ciclos: ensaio exige destinos v17 inicializados')
        if not bundle_active and not cycles_check:
            publisher.recover()  # Resolve an older uncertain load before admitting a candidate.
        if recover_only:
            active = publisher.control()[0]["active"]
            publisher.verify(active)
            return {"status": "success", "publication_verified": True,
                    "gold_rows": active["rows"], "gold_cut_utc": active["cut"]}
        if cycles_check:
            source_control = source._control()
            if source_control[0]['pending'] is not None:
                raise ValueError('Ciclos: fonte pendente')
            source.verify_publication(source_control[0]['active'])
            connection = {'pending': False, 'published': source_control[0]['active']['gold_hash'] is not None}
        else:
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
        rule_snapshots = (source._read_state(source_control[0]['active'])["meta_gold_rule_snapshot"]
                          if cycles_check else source.read("meta_gold_rule_snapshot", settings.monday_board_id))
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
        context_control, context_generation = context_store.control()
        descriptor = context_control['active']
        if context_control['pending'] is not None or not descriptor:
            raise ValueError('Consolidado: cadastro atual nao publicado')
        from zoneinfo import ZoneInfo
        if timestamp(descriptor['cut']).astimezone(ZoneInfo(settings.preferred_timezone)).date() != scheduled.astimezone(ZoneInfo(settings.preferred_timezone)).date():
            raise ValueError('Consolidado: cadastro atual desatualizado')
        context_store.verify(descriptor)
        context_raw, _ = context_objects.get(descriptor['artifact'])
        if context_raw is None or hashlib.sha256(context_raw).hexdigest() != descriptor['sha256']:
            raise ValueError('Consolidado: artefato de cadastro divergente')
        context = [json.loads(line) for line in context_raw.splitlines()]
        if context_store.fingerprint(context) != descriptor['fingerprint']:
            raise ValueError('Consolidado: fingerprint de cadastro divergente')
        rows, report = build(old, new, mapping, old_inputs=frozen_inputs(read_context), current_context=context)
        # Detect external edits as well as conflicting cooperative pipeline writes.
        if cycles_check:
            if source._control() != source_control:
                raise ValueError('Ciclos: fonte mudou durante ensaio')
        else:
            source.check_connection()
        if source.client.get_table(SOURCE).etag != before.etag:
            raise ValueError("Consolidado: fonte mudou durante a leitura")
        if cycles_check:
            from monday_sla_orcamento.cycle_contract import project as validate_cycles
            from monday_sla_orcamento.live_cycles import build as build_cycles
            from sls_orcamento_ppd.rules.business_time import BusinessCalendar

            if context_store.control() != (context_control, context_generation) or destinations.control() != read_control:
                raise ValueError('Ciclos: controle mudou durante ensaio; repetir')
            if not rows:
                raise ValueError('Ciclos: populacao vazia')
            if cycles_bundle_check:
                from monday_sla_orcamento.cycle_destinations import build as build_bundle
                from monday_sla_orcamento.cycle_publication import validate_bundle

                outputs, summary = build_bundle(rows)
                validate_bundle(outputs, summary)
                return {'status': 'cycles_bundle_plan_verified', 'data_modified': False,
                        'publication_verified': False, **summary}
            result = build_cycles(rows, BusinessCalendar('America/Sao_Paulo'),
                                  cut=rows[0]['corte_globocorp_utc'])
            validate_cycles(result)
            return {'status': 'cycles_rehearsal_only', 'data_modified': False,
                    'publication_verified': False, 'source_projects': report['projects'],
                    'source_passages': len(rows), 'candidate_projects': len({r['projeto_id'] for r in result['passagens']}),
                    'excluded_projects': len(result['excluidos']), 'cycles': len(result['ciclos']),
                    'cycles_by_state': dict(Counter(c['situacao'] for c in result['ciclos'])),
                    'passages_by_duration_origin': dict(Counter(p['origem_duracao'] for p in result['passagens'])),
                    'observed_deliveries': sum(c['kpi_entrega_observada'] for c in result['ciclos']),
                    'cycles_with_estimate': sum(c['contem_estimativa'] for c in result['ciclos']),
                    'note': 'Candidato nao publicado. Idade aberta exige evidencia no corte; sem evidencia permanece nula.'}
        evidence = {"table": SOURCE, "etag": before.etag, "history_sha": HISTORY_SHA,
                    "map_sha": MAP_SHA, "scheduled_for": scheduled.isoformat()}
        if bundle_active:
            outputs, split_report = split_destinations(rows)
            split_report['consolidation'] = report
            evidence['cut'] = rows[0]['corte_globocorp_utc'] if rows else None
            if cycles_active:
                return destinations.publish(outputs, split_report, evidence)
            return destinations.publish(outputs, split_report, evidence, publisher)
        return publisher.publish(rows, report, evidence)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--scheduled-for", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--recover-only", action="store_true")
    parser.add_argument("--initialize-destinations", action="store_true")
    args = parser.parse_args()
    try:
        scheduled = datetime.fromisoformat(args.scheduled_for)
        if scheduled.utcoffset() is None:
            raise ValueError("Referencia sem fuso")
        if args.env_file != "globocorp-runtime":
            raise ValueError("Consolidado: seletor de configuracao invalido")
        # Explicit source runtime binding, not a second secret file. Output settings
        # are fixed separately; BQ_TABLE is never changed to the consolidated target.
        options = {'recover_only': args.recover_only}
        if args.initialize_destinations:
            options['initialize_destinations'] = True
        receipt = execute(load_settings(".env"), scheduled, **options)
        with Path(args.result).open("x", encoding="utf-8") as handle:
            json.dump(receipt, handle)
        print(json.dumps({"event": "consolidated_publication_confirmed", **receipt}), flush=True)
    except Exception as error:
        print(json.dumps({"event": "consolidated_worker_failed", "error_type": type(error).__name__}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
