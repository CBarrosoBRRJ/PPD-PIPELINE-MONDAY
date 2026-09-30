"""Whole-project exclusions. Codes are the stable audit interface."""

import re

from ..services.clean import clean_text
from ..services.extract import norm, obj

COLLECTIVES = {"bruno e marrone", "manual do mundo", "podpah"}
# R25 (29/09/2026): pool de talentos segue para o modelo, que mede e separa numa tabela própria.
POOL_REASONS = frozenset({"talento_squad", "talento_multiplo", "talento_nao_individual"})

EXCLUSION_REASONS = {
    "talento_ambas_colunas": "Talentos diferentes em Talentos Exclusivos e Interveniência",
    "talento_multiplo": "Mais de um talento no projeto (pool de talentos)",
    "talento_squad": "Squad de Talentos (pool de talentos)",
    "talento_nao_individual": "Coletivo ou organização identificados",
    # Obsoleto desde 2.3.0: a identidade não precisa de revisão para o SLA; mantido para ler quarentenas antigas.
    "talento_identidade_pendente": "Interveniência sem identidade individual revisada",
    "talento_revisao_manual": "Grafia ou identidade de talento em quarentena manual",
    "marca_revisao_manual": "Grafia ou identidade de Marca em quarentena manual",
}


def talent_decision(snapshot, mapping, catalog):
    talent, inter = (clean_text(snapshot.get(k)) for k in ("talento", "intervenciencia"))
    # Keep both source values available for review, even on excluded projects.
    for value in (talent, inter):
        catalog.get("talento", value)
    reasons = set()
    # Regra de 29/09/2026: o mesmo talento nas duas colunas é válido; talentos diferentes são erro.
    if talent and inter and norm(talent) != norm(inter):
        reasons.add("talento_ambas_colunas")
    values = {v["id"]: v for v in snapshot.get("raw_data", {}).get("column_values", [])}
    structured = obj(values.get(mapping.get("talento"), {}).get("value"))
    ids = structured.get("ids", [])
    if len(set(ids)) > 1:
        reasons.add("talento_multiplo")
    for original in (snapshot.get("talento"), snapshot.get("intervenciencia")):
        value = clean_text(original)
        if not value:
            continue
        normalized = norm(value)
        row = catalog.get("talento", value)
        # R26: grafia em revisão no catálogo não retém o projeto; a revisão segue no catálogo.
        if re.search(r"\bsquad\s+(?:de\s+)?talentos\b", normalized):
            reasons.add("talento_squad")
        if normalized in COLLECTIVES or (
            row["review_status"] == "approved" and row["entity_kind"] != "person"
        ):
            reasons.add("talento_nao_individual")
        # Approved individual identities may contain punctuation; structured
        # multiple selection and both-columns exclusions always take precedence.
        approved_person = row["review_status"] == "approved" and row["entity_kind"] == "person"
        if not approved_person and re.search(r"[,;\n\r+]|\s[&/]\s", original):
            reasons.add("talento_multiplo")
    origin = "talento" if talent else "intervenciencia" if inter else None
    # A revisão do nome no catálogo segue disponível para análises por talento, mas não retém o projeto.
    identity = catalog.resolve("talento", talent or inter, exclusive=bool(talent))
    return sorted(reasons), origin, identity
