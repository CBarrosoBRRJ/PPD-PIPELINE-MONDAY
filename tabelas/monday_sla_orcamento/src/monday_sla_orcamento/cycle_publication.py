"""Atomic four-table publication, explicit additive migration, private recovery journal."""
import hashlib
import json
import math
import uuid
from datetime import datetime

from google.api_core.exceptions import Conflict, NotFound
from google.cloud import bigquery
from sls_orcamento_ppd.db.bq import schema_signature
from sls_orcamento_ppd.rules.business_time import BusinessCalendar

from monday_sla_orcamento.consolidation import FIELDS as BASE_FIELDS
from monday_sla_orcamento.consolidation import timestamp
from monday_sla_orcamento.cycle_contract import project as cycle_rows
from monday_sla_orcamento.cycle_destinations import CONTRACTS, CYCLES, EXTRA, VERSION, projection
from monday_sla_orcamento.destination_publication import CONTRACTS as OLD_CONTRACTS
from monday_sla_orcamento.destination_publication import CONTROL as OLD_CONTROL
from monday_sla_orcamento.destination_publication import DestinationStore, transaction
from monday_sla_orcamento.destination_publication import fingerprint as old_fingerprint
from monday_sla_orcamento.destination_publication import normalize as old_normalize
from monday_sla_orcamento.destinations import QUALITY, QUEUE, SLA
from monday_sla_orcamento.live_cycles import build as live_build
from monday_sla_orcamento.publication import DATASET, PROJECT, canonical

CONTROL = 'cycles-destinations-control.json'
IDENTITY = {'contract': VERSION, 'tables': list(CONTRACTS), 'location': 'US'}


def target(name):
    if name not in CONTRACTS:
        raise ValueError('Ciclos: destino invalido')
    return PROJECT + '.' + DATASET + '.' + name


def schema(name):
    return [bigquery.SchemaField(k, t, mode='REQUIRED' if required else 'NULLABLE')
            for k, (t, required) in CONTRACTS[name].items()]


def typed(name, rows):
    output = []
    for source in rows:
        r = dict(source)
        if set(r) != set(CONTRACTS[name]):
            raise ValueError('Ciclos: schema divergente')
        for key, (kind, required) in CONTRACTS[name].items():
            value = r[key]
            if value is None:
                if required:
                    raise ValueError('Ciclos: obrigatorio nulo')
                continue
            if kind in {'TIMESTAMP', 'DATETIME'}:
                if isinstance(value, datetime):
                    value = value.isoformat()
                r[key] = (timestamp(value) if kind == 'TIMESTAMP' else
                          datetime.fromisoformat(value)).isoformat(timespec='microseconds')
            elif kind == 'FLOAT':
                if type(value) not in (float, int) or not math.isfinite(value):
                    raise ValueError('Ciclos: numero invalido')
                r[key] = float(value)
            elif kind == 'INTEGER' and (type(value) is not int or not -(2**63) <= value < 2**63):
                raise ValueError('Ciclos: inteiro invalido')
            elif kind == 'BOOLEAN' and type(value) is not bool:
                raise ValueError('Ciclos: booleano invalido')
            elif kind == 'STRING' and not isinstance(value, str):
                raise ValueError('Ciclos: texto invalido')
        output.append(r)
    key = 'interval_id' if name == SLA else 'ciclo_id' if name == CYCLES else 'projeto_id'
    if len({r[key] for r in output}) != len(output):
        raise ValueError('Ciclos: chave duplicada')
    return sorted(output, key=lambda r: r[key])


def normalize(name, rows):
    if name in (QUEUE, QUALITY):
        return old_normalize(name, rows)
    result = typed(name, rows)
    if name == SLA:
        base = canonical([{k: r[k] for k in BASE_FIELDS} for r in result])
        if base:
            cuts = {r['corte_globocorp_utc'] for r in base}
            if len(cuts) != 1:
                raise ValueError('Ciclos: cortes divergentes')
            rebuilt = live_build(base, BusinessCalendar('America/Sao_Paulo'), cut=next(iter(cuts)))
            p = {r['interval_id']: r for r in rebuilt['passagens']}
            if rebuilt['excluidos'] or set(p) != {r['interval_id'] for r in base}:
                raise ValueError('Ciclos: projeto indevido na principal')
            expected = typed(SLA, [{**r, **projection(p[r['interval_id']])} for r in base])
            if result != expected:
                raise ValueError('Ciclos: projecao divergente')
    return result


def fingerprint(name, rows):
    return hashlib.sha256(json.dumps(normalize(name, rows), ensure_ascii=False,
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def validate_bundle(outputs, report):
    if set(outputs) != set(CONTRACTS) or not report.get('balanced'):
        raise ValueError('Ciclos: lote incompleto')
    normalized = {name: normalize(name, rows) for name, rows in outputs.items()}
    base = [{k: r[k] for k in BASE_FIELDS} for r in normalized[SLA]]
    if not base:
        raise ValueError('Ciclos: populacao principal vazia')
    live = live_build(base, BusinessCalendar('America/Sao_Paulo'), cut=base[0]['corte_globocorp_utc'])
    if typed(CYCLES, cycle_rows(live)) != normalized[CYCLES]:
        raise ValueError('Ciclos: totais ou relacionamento divergente')
    accepted = {r['projeto_id'] for r in base}
    quality = {r['projeto_id']: r for r in normalized[QUALITY]}
    rejected = set(quality) - accepted
    if (not {r['projeto_id'] for r in normalized[QUEUE]} <= accepted
            or len(accepted) != report['accepted_projects']
            or len(rejected) != report['excluded_projects']
            or len(accepted | set(quality)) != report['source_projects']
            or len(base) + sum(quality[p]['quantidade_passagens'] for p in rejected) != report['source_passages']):
        raise ValueError('Ciclos: populacao nao reconciliada')
    return normalized


class CycleStore:
    def __init__(self, client, objects, timeout=600):
        self.client, self.objects, self.timeout = client, objects, timeout

    def control(self):
        raw, generation = self.objects.get(CONTROL)
        if raw is None:
            raise ValueError('Ciclos: inicializacao explicita necessaria')
        value = json.loads(raw)
        if value['identity'] != IDENTITY:
            raise ValueError('Ciclos: identidade divergente')
        return value, generation

    def verify_previous(self, control):
        raw, generation = self.objects.get(OLD_CONTROL)
        if generation != control['previous_generation'] or json.loads(raw) != control['previous_control']:
            raise ValueError('Ciclos: escritor legado alterou controle')
        for name, fields in OLD_CONTRACTS.items():
            table = self.client.get_table(target(name))
            actual = [dict(r) for r in self.client.list_rows(table)]
            projected = [{k: r[k] for k in fields} for r in actual]
            descriptor = control['previous_control']['active']['tables'][name]
            if (len(projected) != descriptor['rows']
                    or old_fingerprint(name, projected) != descriptor['fingerprint']
                    or any(r.get(k) is not None for r in actual for k in EXTRA if name == SLA)
                    or self.client.get_table(target(name)).etag != table.etag):
                raise ValueError('Ciclos: publicacao anterior alterada')

    def initialize(self):
        raw, _ = self.objects.get(CONTROL)
        if raw is None:
            legacy = DestinationStore(self.client, self.objects, self.timeout)
            old, generation = legacy.control()
            if old['pending'] or old['initializing'] or not old['active']:
                raise ValueError('Ciclos: legado nao esta pronto')
            legacy.verify(old['active'])
            try:
                self.client.get_table(target(CYCLES))
            except NotFound:
                pass
            else:
                raise ValueError('Ciclos: tabela preexistente sem journal')
            self.objects.put_json(CONTROL, {'identity': IDENTITY, 'initializing': True,
                'previous_control': old, 'previous_generation': generation,
                'active': None, 'pending': None}, 0)
        control, generation = self.control()
        if not control['initializing']:
            return
        self.verify_previous(control)
        table = self.client.get_table(target(SLA))
        existing = {f.name: f for f in table.schema}
        expected = {f.name: f for f in schema(SLA)}
        if (not set(BASE_FIELDS) <= set(existing) or not set(existing) <= set(expected)
                or any(existing[k].to_api_repr() != expected[k].to_api_repr() for k in existing)):
            raise ValueError('Ciclos: schema de migracao divergente')
        table.schema = list(table.schema) + [f for k, f in expected.items() if k not in existing]
        self.client.update_table(table, ['schema'])
        new_table = bigquery.Table(target(CYCLES), schema=schema(CYCLES))
        new_table.clustering_fields = ['projeto_id', 'situacao']
        self.client.create_table(new_table, exists_ok=True)
        actual = self.client.get_table(target(CYCLES))
        if schema_signature(actual.schema) != schema_signature(schema(CYCLES)) or list(self.client.list_rows(actual)):
            raise ValueError('Ciclos: tabela inicial divergente')
        self.verify_previous(control)
        control['initializing'] = False
        self.objects.put_json(CONTROL, control, generation)

    def verify(self, descriptor):
        for name in CONTRACTS:
            table = self.client.get_table(target(name))
            rows = [dict(r) for r in self.client.list_rows(table)]
            expected = descriptor['tables'][name]
            if (schema_signature(table.schema) != schema_signature(schema(name))
                    or len(rows) != expected['rows'] or fingerprint(name, rows) != expected['fingerprint']
                    or self.client.get_table(target(name)).etag != table.etag):
                raise ValueError('Ciclos: conteudo remoto divergente')

    def recover(self):
        control, generation = self.control()
        if control['initializing']:
            raise ValueError('Ciclos: inicializacao incompleta')
        pending = control['pending']
        if not pending:
            return
        outputs = {}
        for name, descriptor in pending['tables'].items():
            raw, _ = self.objects.get(descriptor['artifact'])
            if raw is None or hashlib.sha256(raw).hexdigest() != descriptor['sha256']:
                raise ValueError('Ciclos: artefato corrompido')
            outputs[name] = [json.loads(line) for line in raw.splitlines()]
            if len(outputs[name]) != descriptor['rows'] or fingerprint(name, outputs[name]) != descriptor['fingerprint']:
                raise ValueError('Ciclos: fingerprint divergente')
        validate_bundle(outputs, pending['report'])
        sql, definitions = transaction(pending['tables'], self.objects, contracts=CONTRACTS)
        config = bigquery.QueryJobConfig(use_legacy_sql=False, use_query_cache=False,
            maximum_bytes_billed=1073741824, table_definitions=definitions)
        try:
            job = self.client.get_job(pending['job_id'], location='US')
        except NotFound:
            try:
                job = self.client.query(sql, job_config=config, job_id=pending['job_id'], location='US')
            except Conflict:
                job = self.client.get_job(pending['job_id'], location='US')
        actual = job.to_api_repr()['configuration']['query']
        if job.query != sql or actual.get('tableDefinitions', {}) != config.to_api_repr()['query'].get('tableDefinitions', {}):
            raise ValueError('Ciclos: job divergente do journal')
        try:
            job.result(timeout=self.timeout)
        except Exception:
            observed = self.client.get_job(pending['job_id'], location='US')
            if observed.state == 'DONE' and observed.error_result:
                control['pending'] = None
                self.objects.put_json(CONTROL, control, generation)
                raise RuntimeError('Ciclos: transacao recusada; dados anteriores preservados') from None
            raise RuntimeError('Ciclos: resultado incerto; journal preservado') from None
        self.verify(pending)
        control.update(active=pending, pending=None)
        self.objects.put_json(CONTROL, control, generation)

    def publish(self, outputs, report, evidence):
        normalized = validate_bundle(outputs, report)
        self.recover()
        control, generation = self.control()
        if control['active']:
            self.verify(control['active'])
        else:
            self.verify_previous(control)
            table = self.client.get_table(target(CYCLES))
            if list(self.client.list_rows(table)):
                raise ValueError('Ciclos: tabela inicial alterada')
        previous = control['active'] or control['previous_control']['active']
        if timestamp(evidence['cut']) < timestamp(previous['cut']):
            raise ValueError('Ciclos: regressao de corte')
        version, descriptors = uuid.uuid4().hex, {}
        for name, rows in normalized.items():
            raw = b'\n'.join(json.dumps(r, ensure_ascii=False, sort_keys=True).encode() for r in rows)
            if rows:
                raw += b'\n'
            artifact = f'cycles/{version}/{name}.ndjson'
            self.objects.put(artifact, raw, content_type='application/x-ndjson')
            descriptors[name] = {'artifact': artifact, 'rows': len(rows),
                'sha256': hashlib.sha256(raw).hexdigest(), 'fingerprint': fingerprint(name, rows)}
        self.objects.put_json(f'cycles/{version}/report.json', {'quality': report, 'source': evidence})
        control['pending'] = {'tables': descriptors, 'cut': evidence['cut'],
            'job_id': 'monday_cycles_' + version, 'report': report}
        self.objects.put_json(CONTROL, control, generation)
        self.recover()
        return {'status': 'success', 'publication_verified': True, 'gold_cut_utc': evidence['cut'],
            'gold_rows': len(normalized[SLA]), 'gold_projects': report['accepted_projects'],
            'destinations': report['destinations'], 'contract': VERSION}
