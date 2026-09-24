"""Read-only metadata inspection in authorized Cloud Shell; never prints tokens/items."""

import json
import subprocess
import urllib.error
import urllib.request

PROJECT = "gglobo-viu-dados-hdg-prd"
BOARDS = ["18429499488", "18429499631"]


def gcloud(*args):
    return subprocess.check_output(["gcloud", *args, "--project=" + PROJECT],
                                   text=True, stderr=subprocess.PIPE)


def inspect():
    job = json.loads(gcloud("run", "jobs", "describe", "pipeline-monday",
                            "--region=us-central1", "--format=json"))
    containers = job["spec"]["template"]["spec"]["template"]["spec"]["containers"]
    if len(containers) != 1:
        raise ValueError("unexpected_container_count")
    candidates = [v for v in containers[0].get("env", [])
                  if v["name"] in {"MONDAY_API_TOKEN", "TOKEN_MONDAY"}]
    if len(candidates) != 1:
        raise ValueError("token_reference_missing_or_ambiguous")
    token = candidates[0].get("value")
    if token is None:
        ref = candidates[0].get("valueFrom", {}).get("secretKeyRef", {})
        if not ref.get("name") or not ref.get("key"):
            raise ValueError("token_reference_unavailable")
        token = gcloud("secrets", "versions", "access", ref["key"], "--secret=" + ref["name"])
    if not token.strip():
        raise ValueError("empty_token")
    query = """query ($ids: [ID!]!) { boards(ids: $ids) {
      id items_count columns { id title type settings_str } groups { id title }
    } }"""
    request = urllib.request.Request(
        "https://api.monday.com/v2",
        data=json.dumps({"query": query, "variables": {"ids": BOARDS}}).encode(),
        headers={"Authorization": token.strip(), "API-Version": "2026-04",
                 "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.load(response)
    if body.get("errors"):
        raise ValueError("monday_query_failed")
    boards = body.get("data", {}).get("boards", [])
    if {str(b["id"]) for b in boards} != set(BOARDS):
        raise ValueError("board_missing_or_permission_denied")
    for board in boards:
        for column in board["columns"]:
            settings = json.loads(column.pop("settings_str") or "{}")
            if column["type"] == "status":
                column["labels"] = settings.get("labels", {})
    return {"status": "metadata_read_only", "boards": boards}


if __name__ == "__main__":
    try:
        print(json.dumps(inspect(), ensure_ascii=False, indent=2))
    except (subprocess.CalledProcessError, urllib.error.URLError, ValueError, KeyError) as error:
        # No remote body, headers, token, item values or credential-bearing exception.
        print(json.dumps({"status": "inspection_failed", "error_type": type(error).__name__}))
        raise SystemExit(1) from None
