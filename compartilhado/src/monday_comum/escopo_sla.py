"""User-defined title exclusions; never inspects the Marca column."""

import json
import re
import unicodedata

VERSION = "escopo-sla-v3"
INPUTS_IGNORADOS = ("VIU FIRST", "PROATIVO")
TERMOS_IGNORADOS = (
    "UPFRONT", "SEM MARCA", "MARCA EM SIGILO", "MARCA NAO REVELADA",
    "MARCA A DEFINIR", "CURADORIA", "MIDIAKIT", "MIDIA KIT", "LEVOP",
    "ANALISE DAS REDES",
)
PREFIXOS_IGNORADOS = ("PACOTE",)


class InputNaoVerificado(ValueError):
    """Per-item context is unavailable; not equivalent to a confirmed blank."""


def normalizar_titulo(title):
    if title is None:
        return ""
    if not isinstance(title, str):
        raise ValueError("Titulo de projeto deve ser texto ou nulo")
    value = "".join(c for c in unicodedata.normalize("NFKD", title) if not unicodedata.combining(c))
    return " ".join(value.upper().split())


def motivos_exclusao(title):
    value = normalizar_titulo(title)
    reasons = ["titulo_" + term.lower().replace(" ", "_")
               for term in TERMOS_IGNORADOS if term in value]
    # Opening brackets/whitespace are presentation, not a commercial client prefix.
    if re.match(r"^(?:\[\s*)*PACOTE\b", value):
        reasons.append("titulo_prefixo_pacote")
    return tuple(sorted(set(reasons)))


def motivos_input(value):
    normalized = normalizar_titulo(value)
    return ("input_" + normalized.lower().replace(" ", "_"),) if normalized in INPUTS_IGNORADOS else ()


def coluna_input(board):
    matches = [c for c in board["columns"] if normalizar_titulo(c.get("title")) == "TIPO DE INPUT"]
    if len(matches) != 1:
        raise ValueError("Tipo de Input: coluna ausente ou ambigua, nao equivale a valor vazio")
    return matches[0]


def ler_input(column, item):
    matches = [v for v in item.get("column_values", []) if v["id"] == column["id"]]
    if len(matches) != 1:
        raise InputNaoVerificado("Tipo de Input: celula nao recuperada ou duplicada")
    cell = matches[0]
    text = cell.get("text") or cell.get("display_value")
    if text and text.strip():
        return text
    value = cell.get("value")
    value = json.loads(value) if isinstance(value, str) and value else value
    if not value:
        return None
    if column["type"] == "status" and value.get("index") is not None:
        settings = column.get("settings_str") or {}
        settings = json.loads(settings) if isinstance(settings, str) else settings
        labels = settings.get("labels", {})
        index = str(value["index"])
        if index in labels:
            return labels[index]
    raise InputNaoVerificado("Tipo de Input: valor preenchido sem rotulo recuperavel")


def filtrar_projetos(rows, inputs=None):
    """Exclude every passage of a matching board/item; preserve inputs and IDs."""
    excluded = {(r["board_id"], r["item_id"]) for r in rows
                if motivos_exclusao(r.get("projeto_nome")) or (
                    inputs is not None and (r["board_id"], r["item_id"]) not in inputs
                ) or motivos_input(
                    inputs[(r["board_id"], r["item_id"])] if inputs is not None
                    else r.get("tipo_input"))}
    return [r for r in rows if (r["board_id"], r["item_id"]) not in excluded]
