import copy
import json
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import NotFound, PreconditionFailed
from monday_sla_orcamento.publication import (
    TARGET,
    ConsolidatedStore,
    fingerprint,
    public_schema,
)
from pipeline_monday.worker_consolidated import ensure_current


class Objects:
    def __init__(self):
        self.data, self.counter = {}, 0

    def get(self, name):
        return self.data.get(name, (None, 0))

    def put(self, name, raw, generation=0, **kwargs):
        if self.get(name)[1] != generation:
            raise PreconditionFailed("generation")
        self.counter += 1
        self.data[name] = raw, self.counter
        return self.counter

    def put_json(self, name, value, generation=0):
        return self.put(name, json.dumps(value).encode(), generation)

    def uri(self, name):
        return "gs://test/consolidado/" + name

    @contextmanager
    def lock(self):
        yield


class Client:
    def __init__(self, rows, objects):
        self.rows, self.objects = copy.deepcopy(rows), objects
        self.jobs, self.fail, self.unknown, self.lost_ack = {}, False, False, False
        self.etag = "initial"

    def get_table(self, name):
        assert name == TARGET
        return SimpleNamespace(schema=public_schema(self.rows[0]["versao_contrato"]), etag=self.etag, description=None)

    def update_table(self, table, fields):
        assert fields == ["description"]
        return table

    def list_rows(self, _):
        return copy.deepcopy(self.rows)

    def get_job(self, identity, **kwargs):
        if identity not in self.jobs:
            raise NotFound("job")
        return self.jobs[identity]

    def load_table_from_uri(self, uri, target, *, job_id, location, job_config):
        assert target == TARGET and location == "US"
        assert job_config.create_disposition == "CREATE_NEVER"
        job = SimpleNamespace(destination=target, source_uris=[uri], schema=job_config.schema,
                              write_disposition=job_config.write_disposition,
                              create_disposition=job_config.create_disposition,
                              state="RUNNING", error_result=None)

        def result(timeout):
            if self.unknown:
                raise TimeoutError("unknown")
            if self.fail:
                job.state, job.error_result = "DONE", {"reason": "invalid"}
                raise ValueError("failure")
            raw = self.objects.get(uri.removeprefix("gs://test/consolidado/"))[0]
            self.rows = [json.loads(line) for line in raw.splitlines()]
            self.etag, job.state = job_id, "DONE"
        job.result = result
        self.jobs[job_id] = job
        if self.lost_ack:
            job.result(1)
            self.lost_ack = False
            raise ConnectionError("lost acknowledgement")
        return job


@pytest.fixture
def publication():
    # Reuse a real contract-valid test record, without private production data.
    from monday_sla_orcamento.consolidation import FIELDS, VERSION
    row = {key: None for key in FIELDS}
    row.update({k: "test" for k, (kind, required) in FIELDS.items() if kind == "STRING" and required})
    row.update({k: 1 for k, (kind, required) in FIELDS.items() if kind == "INTEGER" and required})
    row.update({k: False for k, (kind, required) in FIELDS.items() if kind == "BOOLEAN" and required})
    row.update(interval_id="one", ordem_etapa=1, ambiente_origem="viu2", entrada_status_utc="2026-09-21T10:00:00Z",
               corte_globocorp_utc="2026-09-22T03:00:00Z", versao_contrato=VERSION,
               validacao_negocio="nao_elegivel_etapa_origem_v1", pendencias_json="[]",
               registro_origem_json="{}")
    from monday_sla_orcamento.consumo import project
    from sls_orcamento_ppd.rules.business_time import BusinessCalendar
    row.update(project(row, BusinessCalendar("America/Sao_Paulo")))
    from monday_sla_orcamento.trajectory import project as trajectory_project
    row.update(trajectory_project([row])[row["interval_id"]])
    from monday_sla_orcamento.estimates import project as estimate_project
    row.update(estimate_project([row], BusinessCalendar("America/Sao_Paulo"))[row["interval_id"]])
    from monday_sla_orcamento.analysis_duration import project as analysis_project
    row.update(analysis_project(row))
    from monday_sla_orcamento.pricing import project as pricing_project
    row.update(pricing_project([row], BusinessCalendar("America/Sao_Paulo"))[row["interval_id"]])
    objects = Objects()
    client = Client([row], objects)
    store = ConsolidatedStore(client, objects)
    store.bootstrap([row])
    candidate = copy.deepcopy(row)
    candidate["corte_globocorp_utc"] = "2026-09-23T03:00:00Z"
    return store, client, [row], [candidate]


def test_atomic_publish_and_idempotent_repeat(publication):
    store, client, _, candidate = publication
    receipt = store.publish(candidate, {}, {})
    assert receipt["publication_verified"] and receipt["status"] == "success"
    assert store.control()[0]["pending"] is None
    assert fingerprint(client.rows) == fingerprint(candidate)
    assert store.publish(candidate, {}, {})["status"] == "skipped"
    assert len(client.jobs) == 1


def test_v2_active_can_be_verified_before_v3_publish(publication):
    store, client, previous, candidate = publication
    old = copy.deepcopy(previous)
    from monday_sla_orcamento.consumo import FIELDS as consumption_fields
    from monday_sla_orcamento.estimates import FIELDS as estimate_fields
    from monday_sla_orcamento.trajectory import FIELDS as trajectory_fields
    for key in {**consumption_fields, **trajectory_fields, **estimate_fields}:
        old[0].pop(key)
    old[0].update(versao_contrato="sla-consolidado-evidencias-v2", validacao_negocio="pendente",
                  elegivel_comparacao=False)
    from monday_sla_orcamento.consolidation import fields_for
    old = [{k: v for k, v in r.items() if k in fields_for(r["versao_contrato"])} for r in old]
    client.rows = old
    control, generation = store.control()
    control["active"]["fingerprint"] = fingerprint(old)
    store.objects.put_json("control.json", control, generation)
    assert store.publish(candidate, {}, {})["publication_verified"]
    with pytest.raises(ValueError, match="contrato atual"):
        store.publish(old, {}, {})


def test_v3_active_schema_upgrades_to_v4(publication):
    from monday_sla_orcamento.consumo import FIELDS as consumption_fields
    from monday_sla_orcamento.estimates import FIELDS as estimate_fields
    from monday_sla_orcamento.trajectory import FIELDS as trajectory_fields
    store, client, previous, candidate = publication
    old = [{k: v for k, v in previous[0].items() if k not in {**consumption_fields, **trajectory_fields, **estimate_fields}}]
    old[0]["versao_contrato"] = "sla-consolidado-etapa-v3"
    from monday_sla_orcamento.consolidation import fields_for
    old = [{k: v for k, v in r.items() if k in fields_for(r["versao_contrato"])} for r in old]
    client.rows = old
    control, generation = store.control()
    control["active"]["fingerprint"] = fingerprint(old)
    store.objects.put_json("control.json", control, generation)
    assert store.publish(candidate, {}, {})["publication_verified"]
    assert set(client.rows[0]) == set(candidate[0])


def test_v4_active_schema_upgrades_to_v5(publication):
    from monday_sla_orcamento.estimates import FIELDS as estimate_fields
    from monday_sla_orcamento.trajectory import FIELDS as trajectory_fields
    store, client, previous, candidate = publication
    old = [{k: v for k, v in previous[0].items() if k not in {**trajectory_fields, **estimate_fields}}]
    old[0]["versao_contrato"] = "sla-consolidado-consumo-v4"
    from monday_sla_orcamento.consolidation import fields_for
    old = [{k: v for k, v in r.items() if k in fields_for(r["versao_contrato"])} for r in old]
    client.rows = old
    control, generation = store.control()
    control["active"]["fingerprint"] = fingerprint(old)
    store.objects.put_json("control.json", control, generation)
    assert store.publish(candidate, {}, {})["publication_verified"]
    assert set(client.rows[0]) == set(candidate[0])


def test_v5_active_schema_upgrades_to_v6(publication):
    from monday_sla_orcamento.estimates import FIELDS as estimate_fields
    store, client, previous, candidate = publication
    old = [{k: v for k, v in previous[0].items() if k not in estimate_fields}]
    old[0]["versao_contrato"] = "sla-consolidado-trajetoria-v5"
    from monday_sla_orcamento.consolidation import fields_for
    old = [{k: v for k, v in r.items() if k in fields_for(r["versao_contrato"])} for r in old]
    client.rows = old
    control, generation = store.control()
    control["active"]["fingerprint"] = fingerprint(old)
    store.objects.put_json("control.json", control, generation)
    assert store.publish(candidate, {}, {})["publication_verified"]
    assert set(client.rows[0]) == set(candidate[0])


def test_v7_active_schema_upgrades_to_pricing_v8(publication):
    from monday_sla_orcamento.consolidation import ANALYSIS_VERSION, fields_for
    store, client, previous, candidate = publication
    old = [{k: v for k, v in previous[0].items() if k in fields_for(ANALYSIS_VERSION)}]
    old[0]["versao_contrato"] = ANALYSIS_VERSION
    client.rows = old
    control, generation = store.control()
    control["active"]["fingerprint"] = fingerprint(old)
    store.objects.put_json("control.json", control, generation)
    assert store.publish(candidate, {}, {})["publication_verified"]
    assert set(client.rows[0]) == set(candidate[0])


def test_v6_active_schema_upgrades_to_v7(publication):
    from monday_sla_orcamento.consolidation import ESTIMATE_VERSION, fields_for
    store, client, previous, candidate = publication
    old = [{k: v for k, v in previous[0].items() if k in fields_for(ESTIMATE_VERSION)}]
    old[0]["versao_contrato"] = ESTIMATE_VERSION
    client.rows = old
    control, generation = store.control()
    control["active"]["fingerprint"] = fingerprint(old)
    store.objects.put_json("control.json", control, generation)
    assert store.publish(candidate, {}, {})["publication_verified"]
    assert set(client.rows[0]) == set(candidate[0])


@pytest.mark.parametrize("failure", ["unknown", "lost_ack"])
def test_uncertain_load_recovers_same_job(publication, failure):
    store, client, _, candidate = publication
    setattr(client, failure, True)
    with pytest.raises((RuntimeError, ConnectionError)):
        store.publish(candidate, {}, {})
    assert store.control()[0]["pending"]
    client.unknown = False
    store.recover()
    assert len(client.jobs) == 1
    assert store.control()[0]["pending"] is None
    assert fingerprint(client.rows) == fingerprint(candidate)


def test_terminal_failure_preserves_previous(publication):
    store, client, initial, candidate = publication
    client.fail = True
    with pytest.raises(RuntimeError):
        store.publish(candidate, {}, {})
    assert fingerprint(client.rows) == fingerprint(initial)
    assert store.control()[0]["pending"] is None


def test_external_edit_blocks_overwrite(publication):
    store, client, _, candidate = publication
    client.rows[0]["projeto_nome"] = "changed"
    with pytest.raises(ValueError):
        store.publish(candidate, {}, {})
    assert not client.jobs


def test_regression_and_empty_blocked(publication):
    store, client, _, candidate = publication
    candidate[0]["corte_globocorp_utc"] = "2026-09-21T03:00:00Z"
    for rows in ([], candidate):
        with pytest.raises(ValueError):
            store.publish(rows, {}, {})
    assert not client.jobs


def test_stale_source_cannot_feed_current_daily():
    scheduled = datetime.fromisoformat("2026-09-23T09:00:00+00:00")
    with pytest.raises(ValueError):
        ensure_current([{"corte_utc": "2026-09-22T03:00:00Z"}], scheduled, "America/Sao_Paulo")
    assert ensure_current([{"corte_utc": "2026-09-23T03:00:00Z"}], scheduled, "America/Sao_Paulo")


def test_corrupt_pending_blocks_recovery(publication):
    store, client, _, candidate = publication
    client.unknown = True
    with pytest.raises(RuntimeError):
        store.publish(candidate, {}, {})
    pending = store.control()[0]["pending"]
    store.objects.data[pending["artifact"]] = (b"bad", 999)
    with pytest.raises(ValueError):
        store.recover()
    assert store.control()[0]["pending"]


def test_wrong_remote_job_blocks_recovery(publication):
    store, client, _, candidate = publication
    client.unknown = True
    with pytest.raises(RuntimeError):
        store.publish(candidate, {}, {})
    next(iter(client.jobs.values())).destination = "other.table"
    with pytest.raises(ValueError):
        store.recover()
    assert store.control()[0]["pending"]


def test_initial_adoption_rejects_other_content(publication):
    _, client, initial, _ = publication
    client.rows[0]["projeto_nome"] = "changed"
    objects = Objects()
    with pytest.raises(ValueError):
        ConsolidatedStore(client, objects).bootstrap(initial)
    assert not objects.data


def test_runtime_selector_uses_existing_injected_source_settings(monkeypatch, tmp_path):
    from pipeline_monday import worker_consolidated as worker

    scheduled = "2026-09-23T09:00:00+00:00"
    result = tmp_path / "result.json"
    monkeypatch.setattr("sys.argv", ["worker", "--env-file", "globocorp-runtime",
                                   "--scheduled-for", scheduled, "--result", str(result)])
    marker = object()
    def settings(path):
        assert path == ".env"
        return marker
    def execute(cfg, at, *, recover_only):
        assert cfg is marker and at.isoformat() == scheduled and not recover_only
        return {"status": "success", "publication_verified": True}
    monkeypatch.setattr(worker, "load_settings", settings)
    monkeypatch.setattr(worker, "execute", execute)
    worker.main()
    assert json.loads(result.read_text())["publication_verified"]
