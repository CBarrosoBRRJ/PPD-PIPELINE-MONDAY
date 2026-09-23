import gzip
import json
from datetime import UTC, datetime

import pytest
from historico_viu2.sla import build_candidate, verified_envelope
from monday_log_viu2.archive import digest


def test_verified_archive_rejects_checksum_and_scope(tmp_path):
    content = gzip.compress(json.dumps({
        "source": "viu2", "board_id": "18393336134", "response": {},
    }).encode())
    (tmp_path / "page.gz").write_bytes(content)
    inventory = {"page.gz": {"sha256": digest(content)}}
    assert verified_envelope(tmp_path, "page.gz", inventory)["source"] == "viu2"
    inventory["page.gz"]["sha256"] = "wrong"
    with pytest.raises(ValueError, match="Checksum"):
        verified_envelope(tmp_path, "page.gz", inventory)
    with pytest.raises(ValueError, match="fora"):
        verified_envelope(tmp_path, "../outside.gz", {})


def test_no_overwrite_and_no_naive_cutoff(tmp_path):
    with pytest.raises(ValueError, match="fuso"):
        build_candidate(tmp_path, tmp_path / "new", datetime(2026, 9, 3))
    with pytest.raises(ValueError, match="sobrescrita"):
        build_candidate(tmp_path, tmp_path, datetime(2026, 9, 3, tzinfo=UTC))


def test_candidate_uses_same_public_contract_without_network(tmp_path, monkeypatch):
    from historico_viu2 import sla

    board = {"id": "18393336134", "created_at": "2026-01-01T00:00:00Z", "columns": [
        {"id": "status_19", "title": "Status", "type": "status",
         "settings_str": json.dumps({"labels": {"7": "Entrada", "0": "Elaboração"}})},
        {"id": "person", "title": "Orçamento", "type": "people"},
        {"id": "input_x", "title": "Tipo de Input", "type": "status", "settings_str": "{}"},
    ]}
    captured = datetime(2026, 1, 3, tzinfo=UTC)
    item = {"id": "123", "name": "Projeto teste", "created_at": "2026-01-01T01:00:00Z",
            "column_values": [{"id": "status_19", "value": '{"index":0}'},
                              {"id": "input_x", "value": None, "text": ""}]}
    event = {"id": "1", "event": "update_column_value", "created_at": "2026-01-01T12:00:00Z",
             "data": json.dumps({"pulse_id": 123, "column_id": "status_19",
                                 "previous_value": {"label": {"index": 7, "text": "Entrada"}},
                                 "value": {"label": {"index": 0, "text": "Elaboração"}}})}
    manifest = {"account_id": "5890468"}
    context = {"captured_at": captured.isoformat()}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    (tmp_path / "context").mkdir()
    (tmp_path / "context/context_manifest.json").write_text(json.dumps(context))
    monkeypatch.setattr(sla, "load_evidence", lambda _: (
        manifest, context, board, [event], [(item, captured)], [],
    ))
    report = build_candidate(tmp_path, tmp_path / "candidate", datetime(2026, 1, 2, tzinfo=UTC))
    assert report["status"] == "draft_not_published"
    assert report["scheduled"] is False
    assert report["rows"] == 2
    with gzip.open(tmp_path / "candidate/sla_orcamento_viu2.ndjson.gz", "rt") as handle:
        rows = [json.loads(line) for line in handle]
    assert rows[0]["duracao_horas"] is None  # Inferred entrance never becomes evidence.
    assert rows[1]["duracao_horas"] == 12
