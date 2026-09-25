"""Alertas dedicados Monday. Executar serialmente no Cloud Shell; sem SMTP."""

import argparse
import json
import subprocess
import uuid
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT = "gglobo-viu-dados-hdg-prd"
BASE = f"https://monitoring.googleapis.com/v3/projects/{PROJECT}"
RECIPIENTS = ("caio.barroso@viu.com.br", "cristina.andrade@viu.com.br",
              "gustavo.siano@viu.com.br")
LABELS = {"pipeline": "monday", "managed_by": "monday-alerts-v1"}
FILTER = f'''resource.labels.project_id="{PROJECT}" AND (
 (resource.type="cloud_run_job" AND resource.labels.job_name="pipeline-monday"
  AND resource.labels.location="us-central1" AND (
   severity>=ERROR OR
   (jsonPayload.event="orchestration_end" AND jsonPayload.status=("failed" OR "partial")) OR
   jsonPayload.event=("snapshot_worker_failed" OR "consolidated_worker_failed")
  )) OR
 (resource.type="cloud_scheduler_job" AND resource.labels.job_id="pipeline-monday-diario"
  AND resource.labels.location="us-central1" AND severity>=ERROR) OR
 (resource.type="global" AND logName="projects/{PROJECT}/logs/pipeline-monday-alert-test"
  AND jsonPayload.event="notification_test" AND jsonPayload.pipeline="pipeline-monday")
)'''


def channel(email):
    return {"displayName": f"pipeline-monday / {email}", "type": "email",
            "labels": {"email_address": email}, "userLabels": LABELS, "enabled": True}


def policy(names):
    return {
        "displayName": "pipeline-monday / falhas de execucao v1",
        "userLabels": LABELS, "enabled": True, "combiner": "OR",
        "conditions": [{"displayName": "Falha Monday ou teste identificado",
                        "conditionMatchedLog": {"filter": FILTER,
                            "labelExtractors": {"evento": "EXTRACT(jsonPayload.event)"}}}],
        "alertStrategy": {"notificationRateLimit": {"period": "900s"},
                          "autoClose": "1800s"},
        "notificationChannels": names,
        "documentation": {"mimeType": "text/markdown", "content": (
            "Pipeline Monday: evento ${log.extracted_label.evento}. "
            "Se evento=notification_test, este e um TESTE DE HOMOLOGACAO, nao falha real. "
            "Caso contrario, conferir Logs Explorer do pipeline-monday e a ultima publicacao. "
            "Nao apagar controles, locks ou tabelas. Nao tocar recursos LIA. "
            "Fechamento automatico do incidente NAO comprova recuperacao dos dados."
        )},
    }


class API:
    def __init__(self):
        # Token somente em memoria. Nao exibir comando de autenticacao nem resposta bruta.
        result = subprocess.run(["gcloud", "auth", "print-access-token"],
                                capture_output=True, text=True, check=False)
        if result.returncode or not result.stdout.strip():
            raise RuntimeError("Autenticacao gcloud indisponivel; nenhum segredo exibido.")
        self.token = result.stdout.strip()

    def request(self, method, url, body=None):
        allowed = (BASE, "https://logging.googleapis.com/v2/entries:write")
        if not any(url == prefix or url.startswith(prefix + "/") for prefix in allowed):
            raise RuntimeError("Endpoint fora do escopo.")
        request = Request(url, method=method,
                          data=None if body is None else json.dumps(body).encode(),
                          headers={"Authorization": "Bearer " + self.token,
                                   "Content-Type": "application/json"})
        try:
            with urlopen(request, timeout=60) as response:
                return json.load(response)
        except HTTPError as error:
            raise RuntimeError(f"HTTP {error.code} em {method}; conferir API/permissoes. "
                               "Nenhum IAM foi alterado; nao repetir em paralelo.") from None

    def listing(self, kind):
        items, token = [], None
        while True:
            url = BASE + "/" + kind
            if token:
                url += "?" + urlencode({"pageToken": token})
            page = self.request("GET", url)
            items.extend(page.get(kind, []))
            token = page.get("nextPageToken")
            if not token:
                return items


def matches(actual, expected):
    """Servidor pode acrescentar campos como name/verificationStatus."""
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(matches(actual.get(k), v)
                                               for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            matches(a, e) for a, e in zip(actual, expected, strict=True))
    return actual == expected


def existing(items, desired):
    candidates = [item for item in items if item.get("displayName") == desired["displayName"]]
    if len(candidates) > 1 or (candidates and not matches(candidates[0], desired)):
        raise RuntimeError("Nome duplicado ou configuracao divergente: revisar; nada sobrescrito.")
    return candidates[0] if candidates else None


def configure(api, mode):
    channels = api.listing("notificationChannels")
    policies = api.listing("alertPolicies")
    desired_channels = [channel(email) for email in RECIPIENTS]
    found = [existing(channels, desired) for desired in desired_channels]
    # Detectar colisao de politica antes de criar canais.
    names = [item["name"] if item else "MISSING" for item in found]
    proposed = policy(names)
    prior = [p for p in policies if p.get("displayName") == proposed["displayName"]]
    update_channels = False
    if prior:
        if len(prior) == 1 and matches(prior[0], policy(names[:2])):
            # Unica migracao autorizada: Caio+Cristina -> adicionar Gustavo.
            update_channels = True
        else:
            existing(policies, proposed)
    if mode == "plan":
        return {"status": "plan_no_writes", "recipients": RECIPIENTS,
                "channels_to_create": sum(item is None for item in found),
                "policy_to_create": not prior,
                "policy_channels_to_update": update_channels, "filter": FILTER}
    if mode == "test":
        if not prior or update_channels or any(item is None for item in found):
            raise RuntimeError("Aplicar e verificar configuracao antes do teste.")
        test_id = str(uuid.uuid4())
        api.request("POST", "https://logging.googleapis.com/v2/entries:write", {"entries": [{
            "logName": f"projects/{PROJECT}/logs/pipeline-monday-alert-test",
            "resource": {"type": "global", "labels": {"project_id": PROJECT}},
            "severity": "NOTICE", "insertId": test_id,
            "jsonPayload": {"event": "notification_test", "pipeline": "pipeline-monday",
                            "message": "TESTE DE HOMOLOGACAO - sem falha real", "test_id": test_id}
        }]})
        return {"status": "test_log_written", "test_id": test_id,
                "email_delivery": "aguardando_confirmacao_dos_tres_destinatarios"}
    for index, desired in enumerate(desired_channels):
        if found[index] is None:
            found[index] = api.request("POST", BASE + "/notificationChannels", desired)
    proposed = policy([item["name"] for item in found])
    if update_channels:
        url = "https://monitoring.googleapis.com/v3/" + prior[0]["name"]
        current = api.request("GET", url)
        if current != prior[0]:
            raise RuntimeError("Politica mudou durante a operacao; repetir plan.")
        configured = api.request("PATCH", url + "?updateMask=notificationChannels", {
            "name": prior[0]["name"], "notificationChannels": proposed["notificationChannels"]})
    else:
        configured = existing(policies, proposed)
    if configured is None:
        configured = api.request("POST", BASE + "/alertPolicies", proposed)
    # Recibo somente depois de GET conferir recursos persistidos.
    for item, desired in zip(found, desired_channels, strict=True):
        saved = api.request("GET", "https://monitoring.googleapis.com/v3/" + item["name"])
        if not matches(saved, desired):
            raise RuntimeError("Canal persistido divergente.")
    saved = api.request("GET", "https://monitoring.googleapis.com/v3/" + configured["name"])
    if not matches(saved, proposed):
        raise RuntimeError("Politica persistida divergente.")
    return {"status": "configured_verified", "policy": configured["name"],
            "channels": [item["name"] for item in found], "email_delivery": "not_tested"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "apply", "test"))
    args = parser.parse_args()
    try:
        print(json.dumps(configure(API(), args.mode), indent=2))
    except (RuntimeError, OSError, ValueError) as error:
        print(json.dumps({"status": "failed", "error_type": type(error).__name__,
                          "message": str(error) if isinstance(error, RuntimeError)
                          else "Falha de transporte/leitura; verificar antes de repetir."}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
