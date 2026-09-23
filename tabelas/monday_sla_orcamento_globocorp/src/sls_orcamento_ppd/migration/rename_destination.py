"""Explicit rebind to an already copied table; never copy, delete or schedule data."""

import copy
import uuid

from ..db.bq import BigQueryStore
from ..db.checkpoint import canonical_json

DESTINATION = "monday_sla_orcamento_globocorp"


def rebind_destination(source, *, apply=False, writers_stopped=False, expected_generation=None):
    if source.settings.bq_table != "sla_orcamento":
        raise ValueError("Migração aceita somente o destino legado sla_orcamento")
    if apply and (not writers_stopped or not expected_generation or expected_generation <= 0):
        raise ValueError("Confirme escritores parados e geração do plano")
    settings = source.settings.model_copy(update={"bq_table": DESTINATION})
    target = BigQueryStore(settings, client=source.client, objects=source.objects)
    with source.lock():
        control, generation = source._control()
        if apply and generation != expected_generation:
            raise ValueError("Estado mudou; gere novo plano")
        if control.get("pending") is not None:
            raise ValueError("Publicação pendente; reconcilie antes de migrar")
        if control["active"].get("gold_hash") is None:
            raise ValueError("Migração exige publicação confirmada")
        source._read_state(control["active"])
        source.verify_publication(control["active"])
        # Existing copy must match the complete schema and public content digest.
        target.verify_publication(control["active"])
        table = target.client.get_table(target.table_id)
        if table.expires is not None:
            raise ValueError("Destino deve estar sem expiração")
        if (table.table_type != "TABLE" or table.location.upper() != settings.bq_location.upper()
                or list(table.clustering_fields or []) != ["board_id", "item_id", "status_id"]):
            raise ValueError("Metadados do destino incompatíveis")
        result = {"source": source.table_id, "target": target.table_id,
                  "control_generation": generation, "applied": False}
        if not apply:
            return result
        backup = "backups/rename_destination_" + uuid.uuid4().hex + "/control.json"
        source.objects.put_json(backup, control)
        saved, _ = source.objects.get(backup)
        if saved != canonical_json(control):
            raise RuntimeError("Backup do controle não reconciliado")
        candidate = copy.deepcopy(control)
        candidate["identity"] = target.identity
        # Immutable state, publication receipts, daily claims and hashes stay untouched.
        source._save_control(candidate, generation)
        actual, _ = target._control()
        if actual != candidate:
            raise RuntimeError("Controle divergente; manter agendas pausadas")
        return {**result, "applied": True, "backup": source.objects.uri(backup)}
