"""Archive Monday logs only. Credentials never enter archive or console output."""

import argparse
import getpass
import json
import os
import socket
import sys
from pathlib import Path

from dotenv import dotenv_values
from monday_log_viu2.archive import BoardArchive
from sls_orcamento_ppd.clients.curl_session import CurlSession
from sls_orcamento_ppd.clients.monday_client import MondayClient
from sls_orcamento_ppd.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--board-id", required=True, type=int)
    parser.add_argument("--source", required=True, choices=["viu2", "globocorp"])
    parser.add_argument("--expected-account-id")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--prompt-token", action="store_true")
    parser.add_argument("--token-stdin", action="store_true", help="Ler credencial de pipe privado")
    parser.add_argument("--ipv4", action="store_true", help="Usar IPv4 mantendo validacao TLS")
    parser.add_argument("--curl", action="store_true", help="Transporte TLS nativo do Windows")
    args = parser.parse_args()
    if args.ipv4:
        import urllib3.util.connection

        urllib3.util.connection.allowed_gai_family = lambda: socket.AF_INET
    if args.token_stdin:
        print("Aguardando credencial via stdin; valor nao sera exibido.", flush=True)
        token = sys.stdin.readline().strip()
    elif args.prompt_token:
        token = getpass.getpass("Token Monday (oculto): ")
    else:
        values = dotenv_values(args.env_file)
        token = os.environ.get("MONDAY_ARCHIVE_TOKEN")
        token = token or values.get("MONDAY_API_TOKEN") or values.get("TOKEN_MONDAY")
    if not token:
        print("Credencial ausente; use arquivo privado ou --prompt-token.", flush=True)
        return 2
    settings = Settings(
        _env_file=None, MONDAY_API_TOKEN=token, MONDAY_BOARD_ID=args.board_id,
        monday_max_retries=3, monday_timeout_seconds=60,
    )
    try:
        result = BoardArchive(
            MondayClient(settings, session=CurlSession() if args.curl else None),
            args.output, args.source
        ).run(args.expected_account_id)
    except Exception as exc:
        print("Resgate incompleto: " + type(exc).__name__ +
              "; arquivos ja capturados preservados.", flush=True)
        return 1
    print(json.dumps({key: result[key] for key in
                      ("status", "unique_events", "earliest_event", "latest_event")}),
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
