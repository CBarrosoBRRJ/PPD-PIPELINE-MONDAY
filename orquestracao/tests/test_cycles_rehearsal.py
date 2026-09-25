import hashlib
import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from monday_sla_orcamento import destination_publication
from pipeline_monday import worker_consolidated as w
from sls_orcamento_ppd.rules.business_time import BusinessCalendar


def test_rehearsal_does_not_lock_recover_bootstrap_or_publish(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('Escrita proibida no ensaio')

    raw = b'{}\n'
    descriptor = {'cut': '2026-09-25T09:00:00Z', 'artifact': 'snapshot',
                  'sha256': hashlib.sha256(raw).hexdigest(), 'fingerprint': 'ok'}
    context_control = ({'active': descriptor, 'pending': None}, 1)
    source_control = ({'active': {'gold_hash': 'ok'}, 'pending': None}, 1)
    dest_control = ({'active': {}, 'pending': None, 'initializing': False}, 1)
    config = SimpleNamespace(bq_project=w.PROJECT, bq_dataset=w.DATASET,
        bq_table='monday_sla_orcamento_globocorp', gcs_bucket=w.BUCKET,
        gcs_prefix='sla_orcamento', bq_location='US', monday_board_id=18429499488,
        monday_status_column_id='status_19', preferred_timezone='America/Sao_Paulo',
        bq_job_timeout_seconds=60)
    new = {'corte_utc': '2026-09-25T03:00:00Z', 'versao_regras': 'r'}
    client = SimpleNamespace(get_table=lambda _: SimpleNamespace(etag='same'),
        query=lambda *a, **k: SimpleNamespace(result=lambda **kw: [{'registro': json.dumps(new)}]))
    source = SimpleNamespace(client=client, lock=forbidden, read=forbidden,
        check_connection=forbidden, _control=lambda: source_control,
        verify_publication=lambda d: None, _read_state=lambda d: {
            'meta_gold_rule_snapshot': [{'versao_regras': 'r',
                'conteudo': {'title_scope_version': w.SCOPE_VERSION}}]})
    monkeypatch.setattr(w, 'get_store', lambda _: source)
    monkeypatch.setattr(w, 'ObjectStore', lambda _: SimpleNamespace(
        lock=forbidden, get=lambda key: (None, 0) if key == 'cycles-destinations-control.json' else (raw, 1), bucket=object()))
    monkeypatch.setattr(w, 'ConsolidatedStore', lambda *a, **k: SimpleNamespace(
        bootstrap=forbidden, recover=forbidden, publish=forbidden))
    monkeypatch.setattr(destination_publication, 'DestinationStore', lambda *a: SimpleNamespace(
        recover=forbidden, publish=forbidden, control=lambda: dest_control))
    monkeypatch.setattr(w, 'SnapshotStore', lambda *a: SimpleNamespace(
        control=lambda: context_control, verify=lambda d: None, fingerprint=lambda r: 'ok'))
    monkeypatch.setattr(w, 'checked_object', lambda *a: b'{}')
    monkeypatch.setattr(w, 'frozen_inputs', lambda _: {})
    monkeypatch.setenv('VIU2_ARCHIVE_PREFIX', 'historico_viu2/test')
    row = {'projeto_id': 'p', 'interval_id': 'i', 'status_nome': 'Entrada',
           'ambiente_origem': 'globocorp', 'entrada_status_utc': '2026-09-24T13:00:00Z',
           'saida_status_utc': None, 'elegivel_comparacao': False,
           'versao_calendario_origem': BusinessCalendar('America/Sao_Paulo').version,
           'corte_globocorp_utc': new['corte_utc']}
    monkeypatch.setattr(w, 'build', lambda *a, **k: ([row], {'projects': 1}))
    result = w.execute(config, datetime(2026, 9, 25, 12, tzinfo=UTC), cycles_check=True)
    assert result['status'] == 'cycles_rehearsal_only'
    assert result['data_modified'] is False
    assert result['cycles'] == 1


def test_rehearsal_rejects_write_options():
    with pytest.raises(ValueError):
        w.execute(None, None, cycles_check=True, initialize_destinations=True)
