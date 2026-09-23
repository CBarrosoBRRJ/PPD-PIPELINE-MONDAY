"""Dedicated consolidated publication journal. Never writes either source table."""

import gzip
import hashlib
import json
import uuid
from datetime import datetime

from google.api_core.exceptions import Conflict, NotFound
from google.cloud import bigquery
from monday_comum.escopo_sla import VERSION as SCOPE_VERSION
from sls_orcamento_ppd.db.bq import schema_signature

from monday_sla_orcamento.consolidation import VERSION, fields_for, schema, timestamp, validate

PROJECT = "gglobo-viu-dados-hdg-prd"
DATASET = "viu_agenciamento"
BUCKET = PROJECT + "-ppd-pipeline-monday"
TARGET = PROJECT + "." + DATASET + ".monday_sla_orcamento"
SOURCE = TARGET + "_globocorp"
HISTORY_SHA = "d0aab3fdb25cb1f3746ee0f1c6db37c419e255034b6ce9786ff3e6d84e78af1e"
MAP_SHA = "486845629229aaa881c38ab87d58cec49811f539642d413d9aa29f07569399eb"
INITIAL_SHA = "980f2b9c034226347699edb9b8bbc76e652e98dcc1be3abada7a4f13ed315b44"
INITIAL_PREFIX = "consolidado/primeira_carga/" + INITIAL_SHA + "/"
IDENTITY = {"format": 1, "table": TARGET, "location": "US",
            "scope_policy": SCOPE_VERSION,
            "contract": VERSION, "history_sha": HISTORY_SHA,
            "map_sha": MAP_SHA}
DESCRIPTION = (
    "Trajetoria datada de projetos selecionados entre viu2 congelado e globocorp. "
    "Atualizacao pelo coordenador pipeline-monday apos verificar a origem e o corte. "
    "KPI por etapa: usar sla_etapa_horas_uteis (NULL fora do KPI), "
    "classificacao_consumo e motivos_inelegibilidade_kpi_json; agrupar por ambiente e status. "
    "Sequencia: projeto_id + ordem_etapa; qualidade_trajetoria e limitacoes_trajetoria_json "
    "descrevem o historico observado, nao homologam completude ou SLA total. "
    "Campos saida_estimada e duracao_estimada sao hipoteses separadas, fora do KPI oficial. "
    "Analise unificada: duracao_analise_horas/horas_uteis com origem_duracao_analise explicita. "
    "Populacao selecionada, nao toda a operacao. Total entre contas NAO aprovado. "
    "Sem data ou correspondencia comprovada: fora da selecao, preservado nas origens."
)


def canonical(rows):
    normalized = []
    for source in rows:
        row = dict(source)
        fields = fields_for(row.get("versao_contrato"))
        if set(row) != set(fields):
            raise ValueError("Consolidado: campos divergentes")
        for key, (kind, _) in fields.items():
            value = row[key]
            if value is None:
                continue
            if isinstance(value, datetime):
                value = value.isoformat()
            if kind == "TIMESTAMP":
                value = timestamp(value).isoformat(timespec="microseconds")
            elif kind == "DATETIME":
                value = datetime.fromisoformat(value).isoformat(timespec="microseconds")
            elif kind == "FLOAT":
                value = float(value)
            row[key] = value
        normalized.append(row)
    normalized.sort(key=lambda r: r["interval_id"])
    validate(normalized)
    return normalized


def fingerprint(rows):
    return hashlib.sha256(json.dumps(canonical(rows), sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def public_schema(version=VERSION):
    return [bigquery.SchemaField.from_api_repr(f) for f in schema(version)]


def checked_object(bucket, path, expected_sha):
    blob = bucket.get_blob(path)
    if blob is None:
        raise ValueError("Consolidado: artefato fixado ausente")
    raw = blob.download_as_bytes(if_generation_match=int(blob.generation))
    if hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ValueError("Consolidado: checksum de entrada divergente")
    return gzip.decompress(raw)


class ConsolidatedStore:
    """Caller holds source lock, then this private destination lock.

    A pending job is always resolved before another candidate. An abrupt death
    leaves the GCS lock: no timed lease or automatic unsafe lock removal.
    """

    def __init__(self, client, objects, *, timeout=600):
        self.client, self.objects, self.timeout = client, objects, timeout

    def control(self):
        raw, generation = self.objects.get("control.json")
        if raw is None:
            raise ValueError("Consolidado: controle nao inicializado")
        value = json.loads(raw)
        if value["identity"] != IDENTITY:
            raise ValueError("Consolidado: identidade divergente")
        return value, generation

    def verify(self, descriptor):
        before = self.client.get_table(TARGET)
        actual = [dict(r) for r in self.client.list_rows(before)]
        version = actual[0].get("versao_contrato") if actual else VERSION
        if schema_signature(before.schema) != schema_signature(public_schema(version)):
            raise ValueError("Consolidado: schema remoto divergente")
        after = self.client.get_table(TARGET)
        if (before.etag != after.etag or len(actual) != descriptor["rows"]
                or fingerprint(actual) != descriptor["fingerprint"]):
            raise ValueError("Consolidado: conteudo remoto divergente")

    def describe(self):
        table = self.client.get_table(TARGET)
        if table.description != DESCRIPTION:
            table.description = DESCRIPTION
            self.client.update_table(table, ["description"])

    def bootstrap(self, initial_rows):
        raw, _ = self.objects.get("control.json")
        if raw is not None:
            self.control()
            return
        rows = canonical(initial_rows)
        if not rows:
            raise ValueError("Consolidado: primeira carga vazia")
        descriptor = {"rows": len(rows), "fingerprint": fingerprint(rows),
                      "cut": rows[0]["corte_globocorp_utc"], "job_id": None}
        self.verify(descriptor)  # Adopt only the exact first load already checked by the operator.
        self.objects.put_json("control.json", {"identity": IDENTITY, "active": descriptor,
                                               "pending": None}, 0)

    def recover(self):
        control, generation = self.control()
        pending = control["pending"]
        if pending is None:
            return
        raw, _ = self.objects.get(pending["artifact"])
        if raw is None or hashlib.sha256(raw).hexdigest() != pending["sha256"]:
            raise ValueError("Consolidado: artefato pendente divergente")
        rows = [json.loads(line) for line in raw.splitlines()]
        if len(rows) != pending["rows"] or fingerprint(rows) != pending["fingerprint"]:
            raise ValueError("Consolidado: recibo pendente divergente")
        uri = self.objects.uri(pending["artifact"])
        try:
            job = self.client.get_job(pending["job_id"], location="US")
        except NotFound:
            config = bigquery.LoadJobConfig(
                schema=public_schema(), source_format="NEWLINE_DELIMITED_JSON",
                write_disposition="WRITE_TRUNCATE", create_disposition="CREATE_NEVER",
                clustering_fields=["projeto_id", "ambiente_origem", "item_id"],
                max_bad_records=0, ignore_unknown_values=False,
            )
            try:
                job = self.client.load_table_from_uri(uri, TARGET, job_id=pending["job_id"],
                                                      location="US", job_config=config)
            except Conflict:
                job = self.client.get_job(pending["job_id"], location="US")
        if (str(job.destination) != TARGET or job.source_uris != [uri]
                or job.write_disposition != "WRITE_TRUNCATE"
                or job.create_disposition != "CREATE_NEVER"
                or schema_signature(job.schema) != schema_signature(public_schema())):
            raise ValueError("Consolidado: job remoto nao corresponde ao journal")
        try:
            job.result(timeout=self.timeout)
        except Exception:
            observed = self.client.get_job(pending["job_id"], location="US")
            if observed.state == "DONE" and observed.error_result:
                control["pending"] = None
                self.objects.put_json("control.json", control, generation)
                raise RuntimeError("Consolidado: carga recusada, publicacao anterior preservada") from None
            raise RuntimeError("Consolidado: resultado incerto, journal preservado") from None
        self.verify(pending)
        self.describe()
        control.update(active=pending, pending=None)
        self.objects.put_json("control.json", control, generation)

    def publish(self, rows, report, source_evidence):
        rows = canonical(rows)
        if not rows:
            raise ValueError("Consolidado: publicacao vazia bloqueada")
        if any(r["versao_contrato"] != VERSION for r in rows):
            raise ValueError("Consolidado: candidato precisa do contrato atual")
        cuts = {r["corte_globocorp_utc"] for r in rows}
        if len(cuts) != 1:
            raise ValueError("Consolidado: multiplos cortes")
        cut = next(iter(cuts))
        self.recover()
        control, generation = self.control()
        self.verify(control["active"])
        if timestamp(cut) < timestamp(control["active"]["cut"]):
            raise ValueError("Consolidado: regressao temporal bloqueada")
        digest = fingerprint(rows)
        if digest == control["active"]["fingerprint"]:
            self.describe()
            return {"status": "skipped", "publication_verified": True,
                    "gold_rows": len(rows), "gold_cut_utc": cut}
        version = uuid.uuid4().hex
        artifact = "generations/" + version + "/consolidated.ndjson"
        raw = b"\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True).encode() for r in rows) + b"\n"
        self.objects.put(artifact, raw, content_type="application/x-ndjson")
        self.objects.put_json("generations/" + version + "/report.json",
                              {"quality": report, "source": source_evidence})
        control["pending"] = {"artifact": artifact, "sha256": hashlib.sha256(raw).hexdigest(),
                              "fingerprint": digest, "rows": len(rows), "cut": cut,
                              "job_id": "monday_consolidado_" + version}
        self.objects.put_json("control.json", control, generation)
        self.recover()
        return {"status": "success", "publication_verified": True, "gold_rows": len(rows),
                "gold_projects": len({r["projeto_id"] for r in rows}), "gold_cut_utc": cut}
