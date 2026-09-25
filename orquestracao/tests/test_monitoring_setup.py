import copy
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "scripts/configure_monitoring_cloudshell.py"
SPEC = importlib.util.spec_from_file_location("monitoring_setup", SOURCE)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class FakeAPI:
    def __init__(self):
        self.items = {"notificationChannels": [], "alertPolicies": []}
        self.writes = []

    def listing(self, kind):
        return copy.deepcopy(self.items[kind])

    def request(self, method, url, body=None):
        if method == "POST":
            self.writes.append((url, body))
            if url.endswith("entries:write"):
                return {}
            kind = url.rsplit("/", 1)[1]
            saved = copy.deepcopy(body)
            saved["name"] = f"projects/{m.PROJECT}/{kind}/{len(self.items[kind]) + 1}"
            self.items[kind].append(saved)
            return saved
        name = url.split("/v3/", 1)[1]
        return next(item for values in self.items.values() for item in values
                    if item["name"] == name)


def test_plan_has_no_writes():
    api = FakeAPI()
    assert m.configure(api, "plan")["channels_to_create"] == 2
    assert not api.writes


def test_apply_idempotent_and_test_separate():
    api = FakeAPI()
    assert m.configure(api, "apply")["status"] == "configured_verified"
    assert len(api.writes) == 3
    m.configure(api, "apply")
    assert len(api.writes) == 3
    assert m.configure(api, "test")["status"] == "test_log_written"
    entry = api.writes[-1][1]["entries"][0]
    assert entry["resource"]["type"] == "global"
    assert entry["jsonPayload"]["event"] == "notification_test"


def test_test_requires_configuration():
    api = FakeAPI()
    with pytest.raises(RuntimeError):
        m.configure(api, "test")
    assert not api.writes


@pytest.mark.parametrize("mutation", ["owner", "disabled", "recipient", "duplicate"])
def test_drift_never_overwrites(mutation):
    api = FakeAPI()
    m.configure(api, "apply")
    item = api.items["notificationChannels"][0]
    if mutation == "owner":
        item["userLabels"] = {}
    elif mutation == "disabled":
        item["enabled"] = False
    elif mutation == "recipient":
        item["labels"]["email_address"] = "other@example.com"
    else:
        api.items["notificationChannels"].append(copy.deepcopy(item))
    with pytest.raises(RuntimeError):
        m.configure(api, "apply")
    assert len(api.writes) == 3


def test_policy_collision_prevents_channel_creation():
    api = FakeAPI()
    api.items["alertPolicies"] = [m.policy(["unrelated-channel"])]
    with pytest.raises(RuntimeError):
        m.configure(api, "apply")
    assert not api.writes


def test_partial_channel_creation_can_resume():
    api = FakeAPI()
    api.request("POST", m.BASE + "/notificationChannels", m.channel(m.RECIPIENTS[0]))
    m.configure(api, "apply")
    assert len(api.writes) == 3


def test_scoped_policy():
    p = m.policy(["one", "two"])
    assert len(p["conditions"]) == 1
    assert 'resource.labels.job_name="pipeline-monday"' in m.FILTER
    assert 'resource.labels.job_id="pipeline-monday-diario"' in m.FILTER
    assert 'resource.labels.location="us-central1"' in m.FILTER
    assert 'jsonPayload.status=("failed" OR "partial")' in m.FILTER
    assert p["alertStrategy"]["autoClose"] == "1800s"
