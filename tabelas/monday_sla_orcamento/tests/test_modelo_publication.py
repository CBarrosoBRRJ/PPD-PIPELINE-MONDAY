import copy
import json
from types import SimpleNamespace

import pytest
from google.api_core.exceptions import NotFound
from monday_sla_orcamento.modelo_publication import CONTROL, ModelStore, schema, target
from monday_sla_orcamento.modelo_v19 import CONTRACTS
from test_consolidated_store import Objects
from test_modelo_v19 import run, trajectory


class Client:
    """BigQuery simulado: executa a transação carregando os artefatos do journal."""

    def __init__(self, objects):
        self.objects, self.rows, self.schemas, self.jobs = objects, {}, {}, {}
        self.fail = self.timeout = False
        self.etag = "e0"

    def get_table(self, name):
        name = str(getattr(name, "reference", name))
        if name not in self.rows:
            raise NotFound("missing")
        return SimpleNamespace(table_id=name, schema=self.schemas[name], etag=self.etag, num_rows=len(self.rows[name]))

    def create_table(self, table, exists_ok=False):
        name = str(table.reference)
        self.rows[name], self.schemas[name] = [], table.schema

    def list_rows(self, table):
        return copy.deepcopy(self.rows[table.table_id])

    def get_job(self, job_id, **kwargs):
        if job_id not in self.jobs:
            raise NotFound("missing")
        return self.jobs[job_id]

    def query(self, sql, *, job_config, job_id, location, job_retry):
        assert job_retry is None  # job_id fixo exige job_retry=None (google-cloud-bigquery)
        assert sql.count("BEGIN TRANSACTION") == 1 and sql.count("INSERT INTO") == len(CONTRACTS)
        job = SimpleNamespace(query=sql, state="RUNNING", error_result=None)

        def result(timeout):
            if self.timeout:
                raise TimeoutError("incerto")
            if self.fail:
                job.state, job.error_result = "DONE", {"reason": "negado"}
                raise ValueError("falha")
            for i, name in enumerate(CONTRACTS):
                external = job_config.table_definitions.get(f"input_{i}")
                path = external.source_uris[0].removeprefix("gs://test/consolidado/") if external else None
                self.rows[target(name)] = ([json.loads(line) for line in self.objects.get(path)[0].splitlines()]
                                           if path else [])
            self.etag, job.state = job_id, "DONE"
        job.result = result
        self.jobs[job_id] = job
        return job


def sample():
    return run(p=trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)]),
               q=trajectory("q", [("Entrada", 1), ("Em revisão", 2)]))


def store():
    objects = Objects()
    return ModelStore(Client(objects), objects), objects


def test_initialize_creates_all_tables_once():
    model, objects = store()
    assert model.initialize()["tabelas"] == len(CONTRACTS)
    assert all(model.client.schemas[target(n)] == schema(n) for n in CONTRACTS)
    assert model.initialize()["status"] == "modelo_v19_ja_inicializado"


def test_refuses_existing_table_without_journal():
    model, _ = store()
    model.client.rows[target("monday_sla_projeto")] = [{"projeto_id": "x"}]  # tabela com dados
    model.client.schemas[target("monday_sla_projeto")] = schema("monday_sla_projeto")
    with pytest.raises(ValueError, match="já existe"):
        model.initialize()
    model, _ = store()
    model.client.rows[target("monday_sla_projeto")] = []
    model.client.schemas[target("monday_sla_projeto")] = schema("monday_sla_ciclo")  # esquema de outra tabela
    with pytest.raises(ValueError, match="já existe"):
        model.initialize()


def test_initialize_resumes_after_partial_failure():
    model, objects = store()
    created = []
    real_create = model.client.create_table

    def flaky(table, exists_ok=False):
        if len(created) == 5:
            raise RuntimeError("queda no meio da inicialização")
        created.append(table)
        real_create(table, exists_ok)
    model.client.create_table = flaky
    with pytest.raises(RuntimeError):
        model.initialize()
    assert objects.get(CONTROL)[0] is None and len(created) == 5
    model.client.create_table = real_create
    assert model.initialize()["tabelas"] == len(CONTRACTS)
    assert all(target(n) in model.client.rows for n in CONTRACTS)


def test_publish_is_atomic_and_verified():
    model, objects = store()
    model.initialize()
    receipt = model.publish(sample(), {"cut": "2026-09-28T03:00:00+00:00"})
    assert receipt["publication_verified"] is True
    assert receipt["tables"]["monday_sla_projeto"] == 2
    control = json.loads(objects.get(CONTROL)[0])
    assert control["pending"] is None and control["active"]["tables"]["monday_sla_ciclo"]["rows"] == 2


def test_failed_transaction_keeps_previous_publication():
    model, objects = store()
    model.initialize()
    model.publish(sample(), {"cut": "2026-09-28T03:00:00+00:00"})
    before = copy.deepcopy(model.client.rows)
    model.client.fail = True
    with pytest.raises(RuntimeError, match="recusada"):
        model.publish(sample(), {"cut": "2026-09-29T03:00:00+00:00"})
    assert model.client.rows == before
    assert json.loads(objects.get(CONTROL)[0])["pending"] is None


def test_uncertain_result_keeps_journal_for_recovery():
    model, objects = store()
    model.initialize()
    model.client.timeout = True
    with pytest.raises(RuntimeError, match="incerto"):
        model.publish(sample(), {"cut": "2026-09-28T03:00:00+00:00"})
    assert json.loads(objects.get(CONTROL)[0])["pending"] is not None
    model.client.timeout = False
    model.recover()
    assert json.loads(objects.get(CONTROL)[0])["active"] is not None


def test_external_edit_and_cut_regression_are_rejected():
    model, _ = store()
    model.initialize()
    model.publish(sample(), {"cut": "2026-09-28T03:00:00+00:00"})
    with pytest.raises(ValueError, match="regressão"):
        model.publish(sample(), {"cut": "2026-09-27T03:00:00+00:00"})
    model.client.rows[target("monday_sla_projeto")].pop()
    with pytest.raises(ValueError, match="divergente"):
        model.publish(sample(), {"cut": "2026-09-29T03:00:00+00:00"})


def test_retire_v18_only_after_verified_v19_publication():
    model, objects = store()
    model.initialize()
    with pytest.raises(ValueError, match="antes de aposentar"):
        model.retire_v18()
    assert model.v18_retired() is False
    model.publish(sample(), {"cut": "2026-09-28T03:00:00+00:00"})
    assert model.retire_v18()["status"] == "v18_aposentada"
    assert model.v18_retired() is True
    model.publish(sample(), {"cut": "2026-09-29T03:00:00+00:00"})  # segue publicando normalmente
    assert json.loads(objects.get(CONTROL)[0])["v18_aposentada"] is True


def test_identity_is_pinned_to_the_published_contract_not_the_rule():
    # A identidade acompanha o contrato (esquema), não a regra de cálculo.
    from monday_sla_orcamento import modelo_publication as pub
    from monday_sla_orcamento import modelo_v19 as m
    assert pub.IDENTITY["contract"] == m.CONTRACT == "modelo-v20-1"
    assert pub.PREVIOUS_IDENTITIES[0]["contract"] == "modelo-v19-1"


def test_upgrade_from_v19_creates_only_new_tables_and_keeps_publication():
    from monday_sla_orcamento import modelo_publication as pub
    model, objects = store()
    model.initialize()
    model.publish(sample(), {"cut": "2026-09-28T03:00:00+00:00"})
    control = json.loads(objects.get(CONTROL)[0])
    # Simula o controle de produção na v19: contrato antigo, sem as 4 tabelas novas.
    control["identity"] = pub.PREVIOUS_IDENTITIES[0]
    for name in set(CONTRACTS) - set(pub.V19_TABLES):
        control["active"]["tables"].pop(name)
        model.client.rows.pop(target(name))
        model.client.schemas.pop(target(name))
    kept = {n: copy.deepcopy(model.client.rows[target(n)]) for n in pub.V19_TABLES}
    objects.put_json(CONTROL, control, objects.get(CONTROL)[1])
    with pytest.raises(ValueError, match="identidade divergente"):
        model.publish(sample(), {"cut": "2026-09-29T03:00:00+00:00"})
    result = model.initialize()
    assert result["status"] == "modelo_contrato_migrado" and len(result["tabelas_novas"]) == 4
    assert {n: model.client.rows[target(n)] for n in pub.V19_TABLES} == kept  # nada existente mudou
    assert model.initialize()["status"] == "modelo_v19_ja_inicializado"
    assert model.publish(sample(), {"cut": "2026-09-29T03:00:00+00:00"})["publication_verified"]
