"""Optional Windows TLS transport; credentials go through stdin, not arguments."""

import json
import subprocess

import requests


class CurlSession:
    def __init__(self):
        self.headers = {}

    def post(self, url, json, timeout):
        # Restrict this credential-bearing transport to the official Monday endpoint.
        if url != "https://api.monday.com/v2":
            raise ValueError("Endpoint nao autorizado para transporte de arquivo")
        config = [f"url = {_quote(url)}", 'request = "POST"']
        config += [f"header = {_quote(k + ': ' + v)}" for k, v in self.headers.items()]
        config += [f"data = {_quote(_json(json))}"]
        result = subprocess.run(
            ["curl.exe", "--config", "-", "--silent", "--show-error", "--ipv4",
             "--connect-timeout", "15", "--max-time", str(timeout),
             "--write-out", "\n%{http_code}"],
            input="\n".join(config), capture_output=True, text=True,
            encoding="utf-8", timeout=timeout + 10,
        )
        if result.returncode:
            raise requests.ConnectionError("Falha de transporte HTTPS; detalhes omitidos")
        body, status = result.stdout.rsplit("\n", 1)
        response = requests.Response()
        response.status_code = int(status)
        response._content = body.encode("utf-8")
        return response


def _quote(value):
    # Curl config quoted strings support escaped backslashes, quotes and newlines.
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace(
        "\r", "\\r"
    ).replace("\n", "\\n") + '"'


def _json(value):
    return json.dumps(value, ensure_ascii=True)
