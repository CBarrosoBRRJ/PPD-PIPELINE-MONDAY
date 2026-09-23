import base64
import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest
from monday_sla_orcamento import consolidation
from test_consolidation import inputs


@pytest.fixture
def publisher(monkeypatch):
    scripts = Path(__file__).resolve().parents[1] / "scripts"
    monkeypatch.syspath_prepend(str(scripts))
    monkeypatch.setitem(sys.modules, "consolidation", consolidation)
    spec = importlib.util.spec_from_file_location("consolidated_publisher_test", scripts / "publish_consolidated.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("failure", [None, "changed_source", "bad_remote", "bad_readback"])
def test_publication_is_scoped_and_reconciles_content(publisher, monkeypatch, tmp_path, failure):
    rows, report = consolidation.build(*inputs())
    schema = consolidation.schema()
    artifacts = {
        "consolidated.ndjson.gz": gzip.compress(b"\n".join(json.dumps(r).encode() for r in rows)),
        "schema.json": json.dumps(schema).encode(), "selected_identity.json.gz": gzip.compress(b"{}"),
    }
    manifest = {"destination": "monday_sla_orcamento", "rows": len(rows), "projects": report["projects"],
                "expected_source_modified": {k: "123" for k in publisher.SOURCES},
                "files": {n: {"sha256": hashlib.sha256(b).hexdigest()} for n, b in artifacts.items()}}
    artifacts["manifest.json"] = json.dumps(manifest).encode()
    for name, content in artifacts.items():
        (tmp_path / name).write_bytes(content)
    posts = []

    class API:
        def request(self, url, method="GET", body=None):
            if method == "POST":
                posts.append(body)
                return {"configuration": body["configuration"], "status": {"state": "DONE"}}
            if "/storage/" in url:
                name = unquote(url).rsplit("/", 1)[-1]
                content = artifacts[name]
                return {"size": len(content), "md5Hash": "wrong" if failure == "bad_remote" else
                        base64.b64encode(hashlib.md5(content).digest()).decode()}
            if any(url.endswith("/" + name) for name in publisher.SOURCES):
                return {"lastModifiedTime": "different" if failure == "changed_source" else "123"}
            if url.endswith("/tables/monday_sla_orcamento"):
                return {"numRows": len(rows), "schema": {"fields": schema}, "lastModifiedTime": "456"}
            return {"location": "US"}

    monkeypatch.setattr(publisher, "GoogleAPI", API)
    monkeypatch.setattr(publisher, "identity", lambda api: None)
    monkeypatch.setattr(publisher, "gcloud", lambda *args, **kwargs: None)
    remote_rows = [dict(r) for r in reversed(rows)]
    if failure == "bad_readback":
        remote_rows[0]["projeto_nome"] = "different"
    def query_output(command, **kwargs):
        assert command[0] == "bq" and "query" in command
        assert not any(arg.startswith("--account") for arg in command)
        return json.dumps([{"registro": json.dumps(r)} for r in remote_rows])

    monkeypatch.setattr(publisher.subprocess, "check_output", query_output)
    if failure:
        with pytest.raises(ValueError):
            publisher.publish(tmp_path)
        assert len(posts) == (1 if failure == "bad_readback" else 0)
    else:
        publisher.publish(tmp_path)
        assert len(posts) == 1
        load = posts[0]["configuration"]["load"]
        assert load["writeDisposition"] == "WRITE_EMPTY"
        assert load["destinationTable"]["tableId"] == "monday_sla_orcamento"


def test_fingerprint_accepts_equivalent_datetime_rendering(publisher):
    rows, _ = consolidation.build(*inputs())
    other = [dict(r) for r in rows]
    for r in other:
        r["entrada_status_utc"] = r["entrada_status_utc"].replace("Z", "+00:00")
        r["entrada_status_local"] = r["entrada_status_local"].replace("T", " ")
    assert publisher.fingerprint(rows) == publisher.fingerprint(other)
