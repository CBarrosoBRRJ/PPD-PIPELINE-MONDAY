"""Validate reviewed cross-account identities. Never infer a match from a name.

This is a private integration contract, not the public SLA schema or an automatic
matching algorithm. Existing source IDs and surrogate keys remain unchanged.
"""

from datetime import datetime
from uuid import UUID

SOURCE_SCOPES = {
    "viu2": ("5890468", 18393336134),
    "globocorp": ("21453629", 18429499488),
}
FIELDS = {
    "projeto_id", "environment", "account_id", "board_id", "item_id",
    "review_status", "evidence_ref", "reviewed_by", "reviewed_at",
}


def approved_project_index(rows):
    """Return native key -> stable project UUID; reject the entire invalid map.

Pending/ambiguous records never participate in joins. Evidence references must
point to a reviewed migration record or business identifier; their truth still
requires human/source verification, not merely passing this structural check.
"""
    result, seen, project_origins = {}, set(), set()
    for row in rows:
        if set(row) != FIELDS:
            raise ValueError("Mapa de projetos: campos incompatíveis")
        environment = row["environment"]
        scope = SOURCE_SCOPES.get(environment)
        if scope is None or (row["account_id"], row["board_id"]) != scope:
            raise ValueError("Mapa de projetos: origem incompatível")
        if type(row["item_id"]) is not int or not 0 < row["item_id"] < 2**63:
            raise ValueError("Mapa de projetos: item inválido")
        key = (environment, row["account_id"], row["board_id"], row["item_id"])
        if key in seen:
            raise ValueError("Mapa de projetos: chave nativa repetida")
        seen.add(key)
        if row["review_status"] not in {"approved", "pending", "ambiguous"}:
            raise ValueError("Mapa de projetos: revisão inválida")
        if row["review_status"] != "approved":
            continue
        try:
            project = str(UUID(row["projeto_id"]))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Mapa de projetos: UUID inválido") from None
        if any(not isinstance(row[k], str) or not row[k].strip()
               for k in ("evidence_ref", "reviewed_by")):
            raise ValueError("Mapa de projetos: aprovação sem evidência/revisor")
        reviewed = row["reviewed_at"]
        if not isinstance(reviewed, datetime) or reviewed.utcoffset() is None:
            raise ValueError("Mapa de projetos: data de revisão sem fuso")
        origin = (project, environment)
        if origin in project_origins:
            raise ValueError("Mapa de projetos: fusão de itens exige revisão específica")
        project_origins.add(origin)
        result[key] = project
    return result
