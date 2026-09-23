import gzip
import hashlib
import json

import pytest
from historico_viu2 import eligibility


def archive(monkeypatch, *, count=1, duplicate=False):
    item = {"id": "1", "column_values": [{"id": "input", "text": "", "value": None}]}
    page = {"board_id": "18393336134", "source": "viu2",
            "response": {"next_items_page": {"items": [item] * (2 if duplicate else 1)}}}
    board = {"response": {"boards": [{"columns": [
        {"id": "input", "title": "Tipo de Input", "type": "status"}]}]}}
    def encode(doc):
        return gzip.compress(json.dumps(doc).encode(), mtime=0)
    files = {"board.json.gz": encode(board), "context/items_0001.json.gz": encode(page)}
    manifest = {"board_id": "18393336134", "source": "viu2", "items": count,
                "files": {"items_0001.json.gz": {"sha256": hashlib.sha256(files["context/items_0001.json.gz"]).hexdigest()}}}
    files["context/context_manifest.json"] = json.dumps(manifest).encode()
    monkeypatch.setattr(eligibility, "BOARD_SHA", hashlib.sha256(files["board.json.gz"]).hexdigest())
    monkeypatch.setattr(eligibility, "CONTEXT_SHA", hashlib.sha256(files["context/context_manifest.json"]).hexdigest())
    return files


def test_frozen_blank_is_verified(monkeypatch):
    files = archive(monkeypatch)
    assert eligibility.frozen_inputs(files.__getitem__) == {(18393336134, 1): None}


@pytest.mark.parametrize("path", ["board.json.gz", "context/context_manifest.json", "context/items_0001.json.gz"])
def test_modified_context_rejected(monkeypatch, path):
    files = archive(monkeypatch)
    files[path] += b"changed"
    with pytest.raises(ValueError, match="checksum"):
        eligibility.frozen_inputs(files.__getitem__)


@pytest.mark.parametrize("kwargs", [{"count": 2}, {"duplicate": True}])
def test_incomplete_or_duplicate_context_rejected(monkeypatch, kwargs):
    files = archive(monkeypatch, **kwargs)
    with pytest.raises(ValueError):
        eligibility.frozen_inputs(files.__getitem__)
