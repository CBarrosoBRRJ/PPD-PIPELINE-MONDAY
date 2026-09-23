"""Bounded sequential execution; no shell commands or credentials in the manifest."""

import json
import re
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

RUNNERS = {"sla_orcamento": "pipeline_monday.worker_sla",
           "monday_sla_orcamento": "pipeline_monday.worker_consolidated"}
PRODUCT_FIELDS = {"id", "runner", "env_file", "depends_on"}


def plan(document):
    if set(document) != {"version", "deadline_seconds", "products"} or document["version"] != 1:
        raise ValueError("Manifesto incompatível")
    deadline = document["deadline_seconds"]
    if type(deadline) is not int or not 1 <= deadline <= 3300:
        raise ValueError("Limite global deve estar entre 1 e 3300 segundos")
    products = document["products"]
    if not isinstance(products, list) or not products:
        raise ValueError("Cadastre ao menos um produto diário")
    by_id, paths = {}, set()
    for product in products:
        if not isinstance(product, dict) or set(product) != PRODUCT_FIELDS:
            raise ValueError("Produto: campos incompatíveis")
        identity = product["id"]
        if not isinstance(identity, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", identity):
            raise ValueError("Produto: identificador inválido")
        if identity in by_id:
            raise ValueError("Produto repetido")
        if product["runner"] not in RUNNERS:
            raise ValueError("Executor não implementado ou não autorizado para rotina diária")
        if not isinstance(product["env_file"], str) or not product["env_file"].strip():
            raise ValueError("Produto exige configuração explícita, sem segredos no manifesto")
        path = str(Path(product["env_file"]).resolve()).casefold() if sys.platform == "win32" else str(Path(product["env_file"]).resolve())
        if path in paths:
            raise ValueError("Produtos devem ter configurações separadas")
        paths.add(path)
        dependencies = product["depends_on"]
        if not isinstance(dependencies, list) or any(not isinstance(d, str) for d in dependencies):
            raise ValueError("Dependências inválidas")
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("Dependência repetida")
        by_id[identity] = product
    if any(d not in by_id for p in products for d in p["depends_on"]):
        raise ValueError("Dependência não cadastrada")
    ordered, pending = [], list(products)
    while pending:
        ready = [p for p in pending if set(p["depends_on"]) <= {p["id"] for p in ordered}]
        if not ready:
            raise ValueError("Ciclo nas dependências")
        ordered.extend(ready)
        pending = [p for p in pending if p not in ready]
    return ordered


def execute_product(product, scheduled_for, timeout):
    """A child owns its memory. Killing it may leave its durable lock for recovery."""
    with tempfile.TemporaryDirectory(prefix="pipeline-monday-") as directory:
        result_file = Path(directory) / "result.json"
        command = [sys.executable, "-m", RUNNERS[product["runner"]],
                   "--env-file", product["env_file"], "--scheduled-for", scheduled_for,
                   "--result", str(result_file)]
        try:
            # Stream existing domain logs; do not accumulate raw logs in parent memory.
            completed = subprocess.run(command, timeout=timeout, check=False, shell=False)
        except subprocess.TimeoutExpired:
            return {"status": "failed", "reason": "timeout_inspect_product_lock"}
        except OSError:
            return {"status": "failed", "reason": "worker_start_failed"}
        if completed.returncode != 0:
            return {"status": "failed", "reason": "worker_failed", "exit_code": completed.returncode}
        if not result_file.exists() or result_file.stat().st_size > 65536:
            return {"status": "failed", "reason": "missing_or_invalid_receipt"}
        try:
            receipt = json.loads(result_file.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return {"status": "failed", "reason": "invalid_receipt"}
        if not isinstance(receipt, dict) or receipt.get("status") not in {"success", "skipped"}:
            return {"status": "failed", "reason": "invalid_receipt"}
        if receipt["status"] == "success" and receipt.get("publication_verified") is not True:
            return {"status": "failed", "reason": "publication_not_verified"}
        allowed = {"status", "publication_verified", "gold_rows", "gold_projects", "gold_cut_utc", "run_id"}
        return {k: v for k, v in receipt.items() if k in allowed}


def run(document, *, execute=execute_product, clock=time.monotonic, scheduled_for=None):
    products = plan(document)  # Validate entire graph before first external operation.
    scheduled_for = scheduled_for or datetime.now(UTC).isoformat()
    timestamp = datetime.fromisoformat(scheduled_for)
    if timestamp.utcoffset() is None:
        raise ValueError("Referência de execução exige fuso")
    started = clock()
    results = {}
    for product in products:
        identity = product["id"]
        if any(results[d]["status"] != "success" and not (
                results[d]["status"] == "skipped" and results[d].get("publication_verified") is True)
               for d in product["depends_on"]):
            results[identity] = {"status": "blocked", "reason": "dependency_not_refreshed"}
            continue
        remaining = document["deadline_seconds"] - (clock() - started)
        if remaining <= 0:
            results[identity] = {"status": "blocked", "reason": "global_deadline"}
            continue
        try:
            results[identity] = execute(product, scheduled_for, remaining)
        except Exception:
            # Never dump exception values, environment, source records or secrets.
            results[identity] = {"status": "failed", "reason": "unexpected_worker_failure"}
        print(json.dumps({"event": "product_end", "product": identity, **results[identity]}), flush=True)
    statuses = {"success" if v["status"] == "skipped" and v.get("publication_verified") is True
                else v["status"] for v in results.values()}
    status = "failed" if statuses & {"failed", "blocked"} else "skipped" if statuses == {"skipped"} else "partial" if "skipped" in statuses else "success"
    return {"event": "orchestration_end", "status": status, "scheduled_for": scheduled_for, "products": results}
