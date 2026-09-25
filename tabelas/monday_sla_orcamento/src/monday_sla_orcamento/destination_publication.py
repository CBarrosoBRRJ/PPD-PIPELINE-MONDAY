"""Three-table transaction with immutable inputs and a recoverable GCS journal.

Caller holds the consolidated destination lock. Initialization is explicit;
no additional persistent staging tables or SQL business transformations.
"""

import hashlib
import json
import math
import uuid
from datetime import datetime

from google.api_core.exceptions import Conflict, NotFound
from google.cloud import bigquery
from sls_orcamento_ppd.db.bq import schema_signature
from sls_orcamento_ppd.rules.business_time import BusinessCalendar

from monday_sla_orcamento.consolidation import FIELDS, timestamp
from monday_sla_orcamento.destinations import (
    QUALITY,
    QUALITY_FIELDS,
    QUEUE,
    QUEUE_FIELDS,
    RULE,
    SLA,
)
from monday_sla_orcamento.publication import DATASET, PROJECT, canonical

CONTRACTS = {SLA: FIELDS, QUEUE: QUEUE_FIELDS, QUALITY: QUALITY_FIELDS}
IDENTITY = {'contract': RULE, 'tables': list(CONTRACTS), 'location': 'US'}
CONTROL = 'destinations-control.json'


def target(name):
    if name not in CONTRACTS:
        raise ValueError('Destinos: tabela fora do escopo')
    return PROJECT + '.' + DATASET + '.' + name


def schema(name):
    return [bigquery.SchemaField(k, t, mode='REQUIRED' if required else 'NULLABLE')
            for k, (t, required) in CONTRACTS[name].items()]


def normalize(name, rows):
    if name == SLA:
        return canonical(rows)
    normalized, seen = [], set()
    for source in rows:
        r = dict(source)
        if set(r) != set(CONTRACTS[name]):
            raise ValueError('Destinos: schema divergente')
        for key, (kind, required) in CONTRACTS[name].items():
            value = r[key]
            if value is None:
                if required:
                    raise ValueError('Destinos: obrigatorio nulo')
                continue
            if kind == 'TIMESTAMP':
                if isinstance(value, datetime):
                    value = value.isoformat()
                r[key] = timestamp(value).isoformat(timespec='microseconds')
            elif kind == 'FLOAT':
                if type(value) not in (float, int) or not math.isfinite(value) or value < 0:
                    raise ValueError('Destinos: duracao invalida')
                r[key] = float(value)
            elif kind == 'INTEGER' and (type(value) is not int or not 0 < value < 2**63):
                raise ValueError('Destinos: inteiro invalido')
            elif kind == 'BOOLEAN' and type(value) is not bool:
                raise ValueError('Destinos: booleano invalido')
            elif kind == 'STRING' and not isinstance(value, str):
                raise ValueError('Destinos: texto invalido')
        if r['projeto_id'] in seen or r['versao_regra'] != RULE:
            raise ValueError('Destinos: chave/regra divergente')
        context = json.loads(r['cadastro_atual_json'])
        if (context.get('board_id') != 18429499488
                or context.get('item_id') != r['item_id_globocorp']
                or context.get('status_nome') != r['status_atual']
                or timestamp(context.get('capturado_em')) != timestamp(r['cadastro_capturado_em'])):
            raise ValueError('Destinos: cadastro divergente')
        if name == QUEUE:
            start, end = timestamp(r['entrada_fila_utc']), timestamp(r['espera_ate_utc'])
            calendar = BusinessCalendar('America/Sao_Paulo')
            if (end < start or end != timestamp(r['cadastro_capturado_em'])
                    or (r['status_atual'] or '').strip().casefold() != 'entrada'
                    or r['versao_calendario'] != calendar.version
                    or abs(r['espera_horas_corridas'] - round((end - start).total_seconds() / 3600, 3)) > 0.001
                    or abs(r['espera_horas_uteis'] - round(calendar.hours(start, end), 3)) > 0.001):
                raise ValueError('Destinos: espera de fila divergente')
        else:
            reasons = json.loads(r['motivos_json'])
            evidence = json.loads(r['evidencias_passagens_json'])
            if (not isinstance(reasons, list) or not reasons
                    or not all(isinstance(v, str) and v for v in reasons)
                    or not isinstance(evidence, list) or len(evidence) != r['quantidade_passagens']
                    or len({v['interval_id'] for v in evidence}) != len(evidence)):
                raise ValueError('Destinos: evidencias de qualidade divergentes')
        seen.add(r['projeto_id'])
        normalized.append(r)
    return sorted(normalized, key=lambda r: r['projeto_id'])


def fingerprint(name, rows):
    return hashlib.sha256(json.dumps(normalize(name, rows), ensure_ascii=False,
        sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def transaction(descriptors, objects, *, contracts=None):
    """Materialize immutable external inputs before starting the DML transaction."""
    contracts = CONTRACTS if contracts is None else contracts
    statements, definitions = [], {}
    for i, name in enumerate(contracts):
        descriptor = descriptors[name]
        columns = ', '.join('`' + key + '`' for key in contracts[name])
        if descriptor['rows']:
            external = bigquery.ExternalConfig('NEWLINE_DELIMITED_JSON')
            external.source_uris = [objects.uri(descriptor['artifact'])]
            external.schema = [bigquery.SchemaField(k, t, mode='REQUIRED' if required else 'NULLABLE')
                               for k, (t, required) in contracts[name].items()]
            external.ignore_unknown_values = False
            external.max_bad_records = 0
            definitions['input_' + str(i)] = external
            statements.append(f'CREATE TEMP TABLE batch_{i} AS SELECT {columns} FROM input_{i};')
        else:
            types = {'INTEGER': 'INT64', 'FLOAT': 'FLOAT64', 'BOOLEAN': 'BOOL'}
            ddl = ', '.join(f'`{k}` {types.get(t, t)}' for k, (t, _) in contracts[name].items())
            statements.append(f'CREATE TEMP TABLE batch_{i} ({ddl});')
        statements.append(f'ASSERT (SELECT COUNT(*) FROM batch_{i}) = {descriptor["rows"]} AS "Contagem divergente";')
    statements.append('BEGIN TRANSACTION;')
    for i, name in enumerate(contracts):
        if not name.replace('_', '').isalnum():
            raise ValueError('Destinos: nome invalido')
        destination = PROJECT + '.' + DATASET + '.' + name
        columns = ', '.join('`' + key + '`' for key in contracts[name])
        statements.extend([f'DELETE FROM `{destination}` WHERE TRUE;',
                           f'INSERT INTO `{destination}` ({columns}) SELECT {columns} FROM batch_{i};'])
    statements.append('COMMIT TRANSACTION;')
    return '\n'.join(statements), definitions


class DestinationStore:
    def __init__(self, client, objects, timeout=600):
        self.client, self.objects, self.timeout = client, objects, timeout

    def control(self):
        raw, generation = self.objects.get(CONTROL)
        if raw is None:
            raise ValueError('Destinos: inicializacao explicita necessaria')
        value = json.loads(raw)
        if value['identity'] != IDENTITY:
            raise ValueError('Destinos: identidade divergente')
        return value, generation

    def initialize(self, legacy):
        raw, _ = self.objects.get(CONTROL)
        if raw is None:
            control, _ = legacy.control()
            if control['pending'] is not None:
                raise ValueError('Destinos: legado pendente')
            legacy.verify(control['active'])
            for name in (QUEUE, QUALITY):
                try:
                    self.client.get_table(target(name))
                except NotFound:
                    continue
                raise ValueError('Destinos: tabela ja existe sem journal')
            self.objects.put_json(CONTROL, {'identity': IDENTITY, 'initializing': True,
                'legacy_active': control['active'], 'active': None, 'pending': None}, 0)
        control, generation = self.control()
        if not control['initializing']:
            return
        legacy.verify(control['legacy_active'])
        for name in (QUEUE, QUALITY):
            table = bigquery.Table(target(name), schema=schema(name))
            table.clustering_fields = ['projeto_id']
            self.client.create_table(table, exists_ok=True)
            actual = self.client.get_table(target(name))
            if schema_signature(actual.schema) != schema_signature(schema(name)) or list(self.client.list_rows(actual)):
                raise ValueError('Destinos: nova tabela nao esta vazia/no schema esperado')
        control['initializing'] = False
        self.objects.put_json(CONTROL, control, generation)

    def verify(self, descriptor):
        for name in CONTRACTS:
            before = self.client.get_table(target(name))
            actual = [dict(r) for r in self.client.list_rows(before)]
            expected = descriptor['tables'][name]
            if (schema_signature(before.schema) != schema_signature(schema(name))
                    or len(actual) != expected['rows']
                    or fingerprint(name, actual) != expected['fingerprint']
                    or self.client.get_table(target(name)).etag != before.etag):
                raise ValueError('Destinos: conteudo remoto divergente')

    def recover(self):
        control, generation = self.control()
        if control['initializing']:
            raise ValueError('Destinos: inicializacao incompleta')
        pending = control['pending']
        if pending is None:
            return
        for name, descriptor in pending['tables'].items():
            raw, _ = self.objects.get(descriptor['artifact'])
            if raw is None or hashlib.sha256(raw).hexdigest() != descriptor['sha256']:
                raise ValueError('Destinos: artefato corrompido')
            rows = [json.loads(line) for line in raw.splitlines()]
            if len(rows) != descriptor['rows'] or fingerprint(name, rows) != descriptor['fingerprint']:
                raise ValueError('Destinos: fingerprint divergente')
        sql, definitions = transaction(pending['tables'], self.objects)
        config = bigquery.QueryJobConfig(use_legacy_sql=False, use_query_cache=False,
            maximum_bytes_billed=1073741824, table_definitions=definitions)
        try:
            job = self.client.get_job(pending['job_id'], location='US')
        except NotFound:
            try:
                job = self.client.query(sql, job_config=config, job_id=pending['job_id'], location='US')
            except Conflict:
                job = self.client.get_job(pending['job_id'], location='US')
        actual_config = job.to_api_repr()['configuration']['query']
        if (job.query != sql or actual_config.get('tableDefinitions', {}) !=
                config.to_api_repr()['query'].get('tableDefinitions', {})):
            raise ValueError('Destinos: job nao corresponde ao journal')
        try:
            job.result(timeout=self.timeout)
        except Exception:
            observed = self.client.get_job(pending['job_id'], location='US')
            if observed.state == 'DONE' and observed.error_result:
                control['pending'] = None
                self.objects.put_json(CONTROL, control, generation)
                raise RuntimeError('Destinos: transacao recusada; dados anteriores preservados') from None
            raise RuntimeError('Destinos: resultado incerto; journal preservado') from None
        self.verify(pending)
        control.update(active=pending, pending=None)
        self.objects.put_json(CONTROL, control, generation)

    def publish(self, outputs, report, evidence, legacy):
        if set(outputs) != set(CONTRACTS) or not report['balanced'] or not report['source_projects']:
            raise ValueError('Destinos: conjunto vazio ou incompleto')
        normalized = {name: normalize(name, rows) for name, rows in outputs.items()}
        project_sets = [{r['projeto_id'] for r in normalized[name]} for name in CONTRACTS]
        if (sum(map(len, project_sets)) != len(set.union(*project_sets))
                or len(set.union(*project_sets)) != report['source_projects']
                or len(normalized[SLA]) + sum(r['quantidade_passagens'] for name in (QUEUE, QUALITY)
                    for r in normalized[name]) != report['source_passages']):
            raise ValueError('Destinos: particao publica nao reconciliada')
        self.recover()
        control, generation = self.control()
        if control['active']:
            self.verify(control['active'])
        else:
            legacy.verify(control['legacy_active'])
            for name in (QUEUE, QUALITY):
                table = self.client.get_table(target(name))
                if schema_signature(table.schema) != schema_signature(schema(name)) or list(self.client.list_rows(table)):
                    raise ValueError('Destinos: tabela inicial alterada externamente')
        cut = evidence['cut']
        previous_cut = (control['active'] or control['legacy_active'])['cut']
        if timestamp(cut) < timestamp(previous_cut):
            raise ValueError('Destinos: regressao de corte')
        version = uuid.uuid4().hex
        descriptors = {}
        for name, rows in normalized.items():
            raw = b'\n'.join(json.dumps(r, ensure_ascii=False, sort_keys=True).encode() for r in rows)
            if rows:
                raw += b'\n'
            artifact = f'destinations/{version}/{name}.ndjson'
            self.objects.put(artifact, raw, content_type='application/x-ndjson')
            descriptors[name] = {'artifact': artifact, 'rows': len(rows),
                'sha256': hashlib.sha256(raw).hexdigest(), 'fingerprint': fingerprint(name, rows)}
        self.objects.put_json(f'destinations/{version}/report.json', {'quality': report, 'source': evidence})
        control['pending'] = {'tables': descriptors, 'cut': cut, 'job_id': 'monday_destinations_' + version}
        self.objects.put_json(CONTROL, control, generation)
        self.recover()
        return {'status': 'success', 'publication_verified': True, 'gold_cut_utc': cut,
                'gold_rows': len(normalized[SLA]),
                'gold_projects': len({r['projeto_id'] for r in normalized[SLA]}),
                'destinations': report['destinations']}
