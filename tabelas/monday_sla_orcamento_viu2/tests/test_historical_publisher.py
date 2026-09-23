import base64
import hashlib
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def publisher(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    spec = importlib.util.spec_from_file_location("historical_publisher_test", scripts / "publish_historical_sla.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_corrupt_package_rejected_before_cloud(publisher, tmp_path):
    (tmp_path / "review.ndjson.gz").write_bytes(b"bad")
    (tmp_path / "schema.json").write_bytes(b"[]")
    with pytest.raises(ValueError):
        publisher.local_payload(tmp_path)


@pytest.mark.parametrize("bad_remote", [False, True])
def test_fixed_target_empty_only_and_remote_integrity(publisher, monkeypatch, tmp_path, bad_remote):
    payload = b"example"
    schema = [{"name": "item_id", "type": "INTEGER", "mode": "REQUIRED"}]
    posts = []

    class API:
        def request(self, url, method="GET", body=None):
            if method == "POST":
                posts.append(body)
                return {"configuration": body["configuration"], "status": {"state": "DONE"}}
            if "/storage/" in url:
                return {"size": len(payload), "md5Hash": "wrong" if bad_remote else
                        base64.b64encode(hashlib.md5(payload).digest()).decode()}
            if "/tables/" in url:
                return {"numRows": "17486", "schema": {"fields": schema}}
            return {"location": "US"}

    monkeypatch.setattr(publisher, "GoogleAPI", API)
    monkeypatch.setattr(publisher, "identity", lambda api: None)
    monkeypatch.setattr(publisher, "gcloud", lambda *args, **kwargs: None)
    monkeypatch.setattr(publisher, "local_payload", lambda root: (payload, schema))
    if bad_remote:
        with pytest.raises(ValueError):
            publisher.publish(tmp_path)
        assert not posts
    else:
        publisher.publish(tmp_path)
        assert len(posts) == 1
        load = posts[0]["configuration"]["load"]
        assert load["writeDisposition"] == "WRITE_EMPTY"
        assert load["destinationTable"]["tableId"] == "monday_sla_orcamento_viu2"
        assert load["maxBadRecords"] == 0
