"""Publicação atômica do modelo v19: todas as tabelas numa transação, journal privado, verificação por hash.

Mesmo padrão da publicação v18 (cycle_publication), com duas diferenças deliberadas:
- verificação do que já está publicado só pelo hash do conteúdo (as regras validam o candidato);
- inicialização cria as tabelas novas; nenhuma tabela v18 é alterada.
"""

import hashlib
import json
import math
import uuid
from datetime import date, datetime

from google.api_core.exceptions import Conflict, NotFound
from google.cloud import bigquery
from sls_orcamento_ppd.db.bq import schema_signature

from monday_sla_orcamento.destination_publication import transaction
from monday_sla_orcamento.modelo_v19 import (
    CLUSTERING,
    CONTRACT,
    CONTRACTS,
    KEYS,
    PARTITION_MONTH,
    RULE,
    instant,
    validate,
)
from monday_sla_orcamento.publication import DATASET, PROJECT

CONTROL = "modelo-v19-control.json"
IDENTITY = {"contract": CONTRACT, "tables": sorted(CONTRACTS), "location": "US"}
# Contratos anteriores que podem ser migrados sem apagar nada: só se criam as tabelas novas (vazias).
V19_TABLES = sorted(set(CONTRACTS) - {"monday_sla_projeto_pool", "monday_sla_sem_entrada", "monday_dim_talento",
                                      "monday_dim_marca", "monday_ponte_talento", "monday_ponte_marca",
                                      "monday_sla_cobertura", "monday_sla_tempo_entrega"})
PREVIOUS_IDENTITIES = ({"contract": "modelo-v19-1", "tables": V19_TABLES, "location": "US"},)
PREFIX = "modelo_v19"


def target(name):
    if name not in CONTRACTS:
        raise ValueError("Modelo v19: destino inválido")
    return f"{PROJECT}.{DATASET}.{name}"


def schema(name):
    return [bigquery.SchemaField(k, t, mode="REQUIRED" if required else "NULLABLE")
            for k, (t, required) in CONTRACTS[name].items()]


def typed(name, rows):
    """Normaliza tipos para comparar conteúdo local e remoto (BigQuery devolve datetime/date)."""
    output = []
    for source in rows:
        r = dict(source)
        if set(r) != set(CONTRACTS[name]):
            raise ValueError(f"Modelo v19: schema divergente em {name}")
        for k, (kind, _) in CONTRACTS[name].items():
            v = r[k]
            if v is None:
                continue
            if kind == "TIMESTAMP":
                r[k] = instant(v).isoformat(timespec="microseconds")
            elif kind == "DATE":
                r[k] = v.isoformat() if isinstance(v, (date, datetime)) else date.fromisoformat(v).isoformat()
            elif kind == "FLOAT":
                if not math.isfinite(float(v)):
                    raise ValueError("Modelo v19: número inválido")
                r[k] = float(v)
        output.append(r)
    return sorted(output, key=lambda r: tuple(str(r[c]) for c in KEYS[name]))


def content_fingerprint(name, rows):
    return hashlib.sha256(json.dumps(typed(name, rows), ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


class ModelStore:
    def __init__(self, client, objects, timeout=600):
        self.client, self.objects, self.timeout = client, objects, timeout

    def control(self):
        raw, generation = self.objects.get(CONTROL)
        if raw is None:
            raise ValueError("Modelo v19: inicialização explícita necessária")
        value = json.loads(raw)
        if value["identity"] != IDENTITY:
            raise ValueError("Modelo v19: identidade divergente")
        return value, generation

    def initialize(self):
        """Cria as tabelas v19 vazias. Idempotente e retomável: se uma tentativa anterior caiu no meio,
        reaproveita as tabelas que ela criou (vazias e com o esquema do contrato); recusa qualquer outra."""
        raw, generation = self.objects.get(CONTROL)
        if raw is not None:
            value = json.loads(raw)
            if value["identity"] == IDENTITY:
                return {"status": "modelo_v19_ja_inicializado"}
            if value["identity"] in PREVIOUS_IDENTITIES:
                return self._upgrade(value, generation)
            raise ValueError("Modelo v19: identidade divergente")
        self._create_tables(CONTRACTS)
        self.objects.put_json(CONTROL, {"identity": IDENTITY, "active": None, "pending": None}, 0)
        return {"status": "modelo_v19_inicializado", "tabelas": len(CONTRACTS)}

    def _create_tables(self, names):
        existing = set()
        for name in names:
            try:
                table = self.client.get_table(target(name))
            except NotFound:
                continue
            if table.num_rows or schema_signature(table.schema) != schema_signature(schema(name)):
                raise ValueError(f"Modelo v19: tabela {name} já existe sem journal")
            existing.add(name)
        for name in names:
            if name in existing:
                continue
            table = bigquery.Table(target(name), schema=schema(name))
            if name in CLUSTERING:
                table.clustering_fields = CLUSTERING[name]
            if name in PARTITION_MONTH:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.MONTH, field=PARTITION_MONTH[name])
            self.client.create_table(table, exists_ok=False)

    def _upgrade(self, control, generation):
        """Migra o contrato: cria só as tabelas novas (vazias) e registra no controle. Nada existente é apagado."""
        if control["pending"]:
            raise ValueError("Modelo v19: publicação pendente; recupere antes de migrar o contrato")
        new = [name for name in CONTRACTS if name not in control["identity"]["tables"]]
        self._create_tables(new)
        if control["active"]:
            for name in new:
                control["active"]["tables"][name] = {"artifact": None, "sha256": None, "rows": 0,
                                                     "fingerprint": content_fingerprint(name, [])}
        previous = control["identity"]["contract"]
        control["identity"] = IDENTITY
        self.objects.put_json(CONTROL, control, generation)
        return {"status": "modelo_contrato_migrado", "de": previous, "para": CONTRACT, "tabelas_novas": new}

    def v18_retired(self):
        raw, _ = self.objects.get(CONTROL)
        return raw is not None and json.loads(raw).get("v18_aposentada") is True

    def retire_v18(self):
        """A v19 vira a publicação única. Só depois de uma publicação v19 verificada."""
        self.recover()
        control, generation = self.control()
        if not control["active"]:
            raise ValueError("Modelo v19: publique e verifique a v19 antes de aposentar a v18")
        self.verify(control["active"])
        control["v18_aposentada"] = True
        self.objects.put_json(CONTROL, control, generation)
        return {"status": "v18_aposentada", "corte_v19": control["active"]["cut"]}

    def verify(self, descriptor):
        for name in CONTRACTS:
            table = self.client.get_table(target(name))
            rows = [dict(r) for r in self.client.list_rows(table)]
            expected = descriptor["tables"][name]
            if (schema_signature(table.schema) != schema_signature(schema(name))
                    or len(rows) != expected["rows"] or content_fingerprint(name, rows) != expected["fingerprint"]
                    or self.client.get_table(target(name)).etag != table.etag):
                raise ValueError(f"Modelo v19: conteúdo remoto divergente em {name}")

    def recover(self):
        control, generation = self.control()
        pending = control["pending"]
        if not pending:
            return
        for descriptor in pending["tables"].values():
            raw, _ = self.objects.get(descriptor["artifact"])
            if raw is None or hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
                raise ValueError("Modelo v19: artefato corrompido")
        sql, definitions = transaction(pending["tables"], self.objects, contracts=CONTRACTS)
        config = bigquery.QueryJobConfig(use_legacy_sql=False, use_query_cache=False,
                                         maximum_bytes_billed=1073741824, table_definitions=definitions)
        try:
            job = self.client.get_job(pending["job_id"], location="US")
        except NotFound:
            try:
                job = self.client.query(sql, job_config=config, job_id=pending["job_id"], location="US", job_retry=None)
            except Conflict:
                job = self.client.get_job(pending["job_id"], location="US")
        if job.query != sql:
            raise ValueError("Modelo v19: job divergente do journal")
        try:
            job.result(timeout=self.timeout)
        except Exception:
            observed = self.client.get_job(pending["job_id"], location="US")
            if observed.state == "DONE" and observed.error_result:
                control["pending"] = None
                self.objects.put_json(CONTROL, control, generation)
                raise RuntimeError("Modelo v19: transação recusada; dados anteriores preservados") from None
            raise RuntimeError("Modelo v19: resultado incerto; journal preservado") from None
        self.verify(pending)
        control.update(active=pending, pending=None)
        self.objects.put_json(CONTROL, control, generation)

    def publish(self, outputs, evidence):
        validate(outputs)
        self.recover()
        control, generation = self.control()
        if control["active"]:
            self.verify(control["active"])
            if instant(evidence["cut"]) < instant(control["active"]["cut"]):
                raise ValueError("Modelo v19: regressão de corte")
        version, descriptors = uuid.uuid4().hex, {}
        for name in CONTRACTS:
            rows = typed(name, outputs[name])
            raw = b"".join(json.dumps(r, ensure_ascii=False, sort_keys=True).encode() + b"\n" for r in rows)
            artifact = f"{PREFIX}/{version}/{name}.ndjson"
            self.objects.put(artifact, raw, content_type="application/x-ndjson")
            descriptors[name] = {"artifact": artifact, "rows": len(rows), "sha256": hashlib.sha256(raw).hexdigest(),
                                 "fingerprint": content_fingerprint(name, rows)}
        self.objects.put_json(f"{PREFIX}/{version}/evidence.json", evidence)
        control["pending"] = {"tables": descriptors, "cut": evidence["cut"], "job_id": "monday_modelo_v19_" + version}
        self.objects.put_json(CONTROL, control, generation)
        self.recover()
        return {"status": "success", "publication_verified": True, "contract": CONTRACT, "regra": RULE,
                "tables": {name: d["rows"] for name, d in descriptors.items()}}
