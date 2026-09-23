"""Read-only, resumable preservation of board activity. Never publishes Gold."""

import gzip
import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sls_orcamento_ppd.utils.time import iso, parse_timestamp

LOG_QUERY = """
query ($ids: [ID!]!, $limit: Int!, $page: Int!,
       $from: ISO8601DateTime!, $to: ISO8601DateTime!) {
  boards(ids: $ids) {
    activity_logs(limit: $limit, page: $page, from: $from, to: $to) {
      id event data created_at user_id account_id entity
    }
  }
}
"""


def digest(content):
    return hashlib.sha256(content).hexdigest()


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")


class BoardArchive:
    def __init__(self, client, directory, source, *, limit=500, split_at=9000):
        self.client = client
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.source = source
        self.limit = limit
        self.split_at = split_at
        self.accepted = []
        self.windows = []
        self.inventory = {}

    def capture(self, name, query, variables):
        """Each response is durable before the next network request."""
        path = self.directory / name
        checksum = path.with_suffix(path.suffix + ".sha256")
        request = {"query": query, "variables": variables}
        if path.exists():
            content = path.read_bytes()
            if not checksum.exists() or checksum.read_text().strip() != digest(content):
                raise ValueError("Arquivo local sem integridade comprovada; preservar e revisar")
            envelope = json.loads(gzip.decompress(content))
            if envelope["request"] != request or envelope["source"] != self.source:
                raise ValueError("Arquivo pertence a outra consulta/origem")
        else:
            response = self.client.query(query, variables)
            envelope = {
                "source": self.source,
                "board_id": str(self.client.settings.monday_board_id),
                "api_version": self.client.settings.monday_api_version,
                "captured_at": iso(datetime.now(UTC)),
                "request": request,
                "response": response,
            }
            content = gzip.compress(encode(envelope), mtime=0)
            with path.open("xb") as stream:
                stream.write(content)
            with checksum.open("x", encoding="ascii") as stream:
                stream.write(digest(content) + "\n")
        self.inventory[name] = {"sha256": digest(content), "bytes": len(content)}
        return envelope["response"]

    def window(self, start, end):
        prefix = start.strftime("%Y%m%dT%H%M%S") + "_" + end.strftime("%Y%m%dT%H%M%S")
        seen = set()
        pages = []
        page = 1
        while True:
            name = f"logs_{prefix}_{page:05d}.json.gz"
            data = self.capture(
                name, LOG_QUERY,
                {"ids": [str(self.client.settings.monday_board_id)],
                 "limit": self.limit, "page": page, "from": iso(start), "to": iso(end)},
            )
            if len(data.get("boards", [])) != 1:
                raise ValueError("Quadro ausente durante resgate")
            logs = data["boards"][0]["activity_logs"]
            ids = [str(row["id"]) for row in logs]
            repeated = len(set(ids)) != len(ids) or bool(seen.intersection(ids))
            seen.update(ids)
            pages.append(name)
            # Split well before Monday's documented 10,000-event ceiling.
            if repeated or len(seen) >= self.split_at:
                seconds = int((end - start).total_seconds())
                if seconds < 2:
                    raise ValueError("Janela saturada/repetida; completude nao comprovada")
                middle = start + timedelta(seconds=seconds // 2)
                self.window(middle, end)
                self.window(start, middle)
                return
            if not logs:
                self.accepted.extend(pages)
                self.windows.append({"from": iso(start), "to": iso(end), "events": len(seen)})
                print(f"Janela concluida: {iso(start)} / {iso(end)}; eventos={len(seen)}",
                      flush=True)
                return
            page += 1

    def run(self, expected_account_id=None):
        manifest = {
            "format_version": 1, "source": self.source,
            "board_id": str(self.client.settings.monday_board_id),
            "status": "in_progress", "coverage": "available_api_history_only",
            "limitations": [
                "Retention/deleted/inaccessible events may be missing.",
                "Captured board metadata is current, not a migration-time snapshot.",
                "Migration cutoff and cross-account identity mapping are not established.",
                "No Gold publication or source mutation.",
            ],
        }
        try:
            account = self.capture("account.json.gz", "query { me { account { id } } }", {})
            account_id = str(account["me"]["account"]["id"])
            manifest["account_id"] = account_id
            if expected_account_id and account_id != str(expected_account_id):
                raise ValueError("Conta autenticada diferente da origem esperada")
            board_response = self.capture(
                "board.json.gz",
                """query ($ids: [ID!]!) { boards(ids: $ids) {
                  id name created_at items_count columns { id title type settings_str }
                } }""",
                {"ids": [str(self.client.settings.monday_board_id)]},
            )
            if len(board_response.get("boards", [])) != 1:
                raise ValueError("Token sem acesso ao quadro de origem")
            board = board_response["boards"][0]
            if str(board["id"]) != str(self.client.settings.monday_board_id):
                raise ValueError("Quadro retornado diferente da origem")
            # Cached metadata fixes the extraction boundary across restarts.
            metadata = json.loads(gzip.decompress((self.directory / "board.json.gz").read_bytes()))
            start = parse_timestamp(board["created_at"]).replace(microsecond=0)
            end = parse_timestamp(metadata["captured_at"]).replace(microsecond=0)
            manifest.update(requested_from=iso(start), requested_to=iso(end))
            edge = end
            while edge > start:
                lower = max(start, edge - timedelta(days=7))
                self.window(lower, edge)
                edge = lower
            manifest.update(self.verify_events())
            manifest["status"] = "complete_available_api_history"
        except Exception as exc:
            manifest["status"] = "incomplete"
            manifest["error_type"] = type(exc).__name__
            raise
        finally:
            manifest["files"] = self.inventory
            manifest["accepted_log_pages"] = self.accepted
            manifest["completed_windows"] = self.windows
            manifest["updated_at"] = iso(datetime.now(UTC))
            target = self.directory / "manifest.json"
            temporary = self.directory / "manifest.json.tmp"
            temporary.write_bytes(encode(manifest))
            temporary.replace(target)
        return manifest

    def verify_events(self):
        seen = {}
        timestamps = []
        invalid_timestamps = 0
        duplicates = 0
        for name in self.accepted:
            content = (self.directory / name).read_bytes()
            if digest(content) != self.inventory[name]["sha256"]:
                raise ValueError("Arquivo alterado durante verificacao")
            data = json.loads(gzip.decompress(content))["response"]
            for row in data["boards"][0]["activity_logs"]:
                key = str(row["account_id"]), str(row["id"])
                fingerprint = digest(encode(row))
                if key in seen:
                    if seen[key] != fingerprint:
                        raise ValueError("Mesmo evento com conteudos conflitantes")
                    duplicates += 1
                    continue
                seen[key] = fingerprint
                try:
                    timestamps.append(parse_timestamp(row["created_at"]))
                except (ValueError, TypeError, OverflowError):
                    invalid_timestamps += 1
        return {
            "unique_events": len(seen), "boundary_duplicates": duplicates,
            "invalid_timestamps_preserved": invalid_timestamps,
            "earliest_event": iso(min(timestamps)) if timestamps else None,
            "latest_event": iso(max(timestamps)) if timestamps else None,
        }
