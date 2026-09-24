"""Restricted current-board snapshots, durable publication journal and full verification."""

import hashlib
import json
import uuid
from datetime import datetime

from google.api_core.exceptions import Conflict, NotFound
from google.cloud import bigquery
from sls_orcamento_ppd.db.bq import schema_signature

PROJECT = 'gglobo-viu-dados-hdg-prd'
BUCKET = PROJECT + '-ppd-pipeline-monday'
TARGETS = {'monday_backlog_agenciamento_2026': 18429499488,
           'monday_talentos_exclusivos': 18429499631}
BASE = {'board_id': 'INTEGER', 'item_id': 'INTEGER', 'item_nome': 'STRING',
        'grupo_id': 'STRING', 'grupo_nome': 'STRING', 'estado_item': 'STRING', 'capturado_em': 'TIMESTAMP',
        'criado_em_origem': 'TIMESTAMP', 'atualizado_em_origem': 'TIMESTAMP',
        'versao_contrato': 'STRING'}


class SnapshotStore:
    def __init__(self, client, objects, spec, timeout=600):
        if TARGETS.get(spec['table']) != spec['board_id']:
            raise ValueError('Snapshot: destino nao autorizado')
        self.client, self.objects, self.spec, self.timeout = client, objects, spec, timeout
        self.target = PROJECT + '.viu_agenciamento.' + spec['table']
        self.fields = {**BASE, **dict.fromkeys(spec['columns'], 'STRING')}
        self.schema = [bigquery.SchemaField(k, v, mode='REQUIRED' if k in {
            'board_id', 'item_id', 'item_nome', 'capturado_em', 'versao_contrato'
        } else 'NULLABLE') for k, v in self.fields.items()]
        self.identity = {'table': self.target, 'board_id': spec['board_id'],
                         'contract': 'board-snapshot-v1', 'location': 'US'}

    def canonical(self, rows):
        result, seen = [], set()
        for source in rows:
            row = dict(source)
            if set(row) != set(self.fields):
                raise ValueError('Snapshot: campos divergentes')
            for key, kind in self.fields.items():
                value = row[key]
                if value is None:
                    if key in {'board_id', 'item_id', 'item_nome', 'capturado_em', 'versao_contrato'}:
                        raise ValueError('Snapshot: obrigatorio ausente')
                    continue
                if kind == 'INTEGER':
                    if type(value) is not int or not 0 < value < 2**63:
                        raise ValueError('Snapshot: ID invalido')
                elif kind == 'TIMESTAMP':
                    parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))
                    if parsed.utcoffset() is None:
                        raise ValueError('Snapshot: data sem fuso')
                    from datetime import UTC
                    row[key] = parsed.astimezone(UTC).isoformat(timespec='microseconds')
                elif not isinstance(value, str):
                    raise ValueError('Snapshot: texto invalido')
            if (row['board_id'] != self.spec['board_id'] or row['item_id'] in seen
                    or row['versao_contrato'] != 'board-snapshot-v1'):
                raise ValueError('Snapshot: identidade duplicada/divergente')
            seen.add(row['item_id'])
            result.append(row)
        return sorted(result, key=lambda r: r['item_id'])

    def fingerprint(self, rows):
        return hashlib.sha256(json.dumps(self.canonical(rows), sort_keys=True,
                                         ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()

    def control(self):
        raw, generation = self.objects.get('control.json')
        if raw is None:
            try:
                self.client.get_table(self.target)
            except NotFound:
                value = {'identity': self.identity, 'active': None, 'pending': None}
                self.objects.put_json('control.json', value, 0)
                return self.control()
            raise ValueError('Snapshot: tabela existente sem controle; nao adotar automaticamente')
        value = json.loads(raw)
        if value['identity'] != self.identity:
            raise ValueError('Snapshot: identidade do controle divergente')
        return value, generation

    def verify(self, descriptor):
        before = self.client.get_table(self.target)
        rows = [dict(r) for r in self.client.list_rows(before)]
        if (schema_signature(before.schema) != schema_signature(self.schema)
                or len(rows) != descriptor['rows'] or self.fingerprint(rows) != descriptor['fingerprint']
                or self.client.get_table(self.target).etag != before.etag):
            raise ValueError('Snapshot: verificacao remota divergente')

    def recover(self):
        control, generation = self.control()
        pending = control['pending']
        if pending is None:
            return
        raw, _ = self.objects.get(pending['artifact'])
        if raw is None or hashlib.sha256(raw).hexdigest() != pending['sha256']:
            raise ValueError('Snapshot: artefato pendente corrompido')
        rows = [json.loads(line) for line in raw.splitlines()]
        if len(rows) != pending['rows'] or self.fingerprint(rows) != pending['fingerprint']:
            raise ValueError('Snapshot: conteudo pendente divergente')
        uri = self.objects.uri(pending['artifact'])
        disposition = 'WRITE_TRUNCATE' if control['active'] else 'WRITE_EMPTY'
        try:
            job = self.client.get_job(pending['job_id'], location='US')
        except NotFound:
            config = bigquery.LoadJobConfig(schema=self.schema, source_format='NEWLINE_DELIMITED_JSON',
                                            write_disposition=disposition, max_bad_records=0,
                                            ignore_unknown_values=False, clustering_fields=['item_id'])
            try:
                job = self.client.load_table_from_uri(uri, self.target, job_id=pending['job_id'],
                                                      location='US', job_config=config)
            except Conflict:
                job = self.client.get_job(pending['job_id'], location='US')
        if (str(job.destination) != self.target or job.source_uris != [uri]
                or job.write_disposition != disposition
                or schema_signature(job.schema) != schema_signature(self.schema)):
            raise ValueError('Snapshot: job nao corresponde ao journal')
        try:
            job.result(timeout=self.timeout)
        except Exception:
            observed = self.client.get_job(pending['job_id'], location='US')
            if observed.state == 'DONE' and observed.error_result:
                control['pending'] = None
                self.objects.put_json('control.json', control, generation)
                raise RuntimeError('Snapshot: carga falhou; anterior preservada') from None
            raise RuntimeError('Snapshot: resultado incerto; pendencia preservada') from None
        self.verify(pending)
        control.update(active=pending, pending=None)
        self.objects.put_json('control.json', control, generation)

    def publish(self, rows):
        rows = self.canonical(rows)
        if not rows or len({r['capturado_em'] for r in rows}) != 1:
            raise ValueError('Snapshot: captura vazia ou referencias multiplas')
        self.recover()
        control, generation = self.control()
        if control['active']:
            self.verify(control['active'])
            if rows[0]['capturado_em'] < control['active']['cut']:
                raise ValueError('Snapshot: regressao temporal')
        version = uuid.uuid4().hex
        artifact = 'generations/' + version + '/snapshot.ndjson'
        raw = b'\n'.join(json.dumps(r, ensure_ascii=False, sort_keys=True).encode() for r in rows) + b'\n'
        self.objects.put(artifact, raw, content_type='application/x-ndjson')
        control['pending'] = {'artifact': artifact, 'sha256': hashlib.sha256(raw).hexdigest(),
                              'rows': len(rows), 'fingerprint': self.fingerprint(rows),
                              'cut': rows[0]['capturado_em'], 'job_id': 'monday_snapshot_' + version}
        self.objects.put_json('control.json', control, generation)
        self.recover()
        return {'status': 'success', 'publication_verified': True, 'gold_rows': len(rows),
                'gold_cut_utc': rows[0]['capturado_em']}
