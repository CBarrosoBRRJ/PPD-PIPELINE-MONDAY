"""Observed pricing cycles; pauses excluded from both clocks, never bridge accounts.

Totals occur only on the delivery passage. Source passages and stage KPIs stay intact.
"""

import json
import unicodedata
from collections import defaultdict
from datetime import datetime

RULE = "precificacao-status-atuais-v1"
FIELDS = {
    "versao_regra_precificacao": ("STRING", True),
    "papel_precificacao": ("STRING", True),
    "ciclo_precificacao_id": ("STRING", False),
    "situacao_ciclo_precificacao": ("STRING", True),
    "motivos_ciclo_precificacao_json": ("STRING", True),
    "entrega_precificacao_observada": ("BOOLEAN", True),
    "inicio_precificacao_utc": ("TIMESTAMP", False),
    "fim_precificacao_utc": ("TIMESTAMP", False),
    "precificacao_horas_corridas": ("FLOAT", False),
    "precificacao_horas_uteis": ("FLOAT", False),
    "pausas_precificacao_horas_corridas": ("FLOAT", False),
    "pausas_precificacao_horas_uteis": ("FLOAT", False),
    "janela_precificacao_horas_corridas": ("FLOAT", False),
    "contribuicao_precificacao_horas_corridas": ("FLOAT", False),
    "contribuicao_precificacao_horas_uteis": ("FLOAT", False),
}


def normalize(value):
    return " ".join(unicodedata.normalize("NFC", value or "").casefold().split())


WORK = {normalize(v) for v in (
    "Entrada", "Em Elaboração", "Em Elaboração - Orçamentos",
    "Em elaboração (Produção)", "Em revisão", "Em revisão (Planejamento)",
    "Em elaboração - GP", "Em elaboração - Conteúdo", "Em elaboração - Audiência",
    "Em elaboração - Cotação Gestão de Elenco", "Em elaboração - Validação Gestão Esporte",
    "Em revisão - Validação Talento", "Em revisão - Validação Talent Manager",
    "Em Elaboração - Validação Talents", "Em elaboração - Cotação Externa",
)}
PAUSES = {normalize(v) for v in ("Standby", "Em elaboração - Retorno Marca/Executivo")}
TERMINALS = {normalize(v) for v in ("Encerrado", "Declinado pelo Mercado", "Declinado Internamente")}


def role(row):
    label = normalize(row.get("status_nome"))
    if label == "aguardando feedback":
        return "entrega"
    if label in PAUSES:
        return "pausa"
    if label in TERMINALS:
        return "terminal_sem_entrega"
    if label in WORK:
        return "inicio" if label == "entrada" else "trabalho"
    return "nao_mapeado"


def time(value):
    if value is None:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("Precificacao: timestamp sem fuso")
    return result


def project(rows, calendar):
    """Project without mutation. An explicit new Entrada starts a new attempt.

    A repeated Entrada before delivery invalidates the unfinished attempt. Unknown
    events, gaps and ineligible intervals block cycle approval, even for pauses.
    Group by project AND origin: identity mapping is not migration continuity.
    """
    result, groups = {}, defaultdict(list)
    for row in rows:
        key = row["interval_id"]
        if key in result:
            raise ValueError("Precificacao: passagem duplicada")
        result[key] = {k: None for k in FIELDS}
        result[key].update(
            versao_regra_precificacao=RULE, papel_precificacao=role(row),
            situacao_ciclo_precificacao="sem_entrada_comprovada",
            motivos_ciclo_precificacao_json="[]", entrega_precificacao_observada=False,
        )
        groups[row["projeto_id"], row["ambiente_origem"]].append(row)

    def close(chain, state, reasons, delivery=None):
        if not chain:
            return
        start = time(chain[0]["entrada_status_utc"])
        end = time(delivery["entrada_status_utc"]) if delivery else None
        members = [*chain, *([delivery] if delivery else [])]
        approved = state == "entregue_observado" and not reasons
        if state == "entregue_observado" and reasons:
            state = "evidencia_insuficiente"
        for r in members:
            out = result[r["interval_id"]]
            out.update(ciclo_precificacao_id=chain[0]["interval_id"],
                       inicio_precificacao_utc=chain[0]["entrada_status_utc"],
                       fim_precificacao_utc=delivery["entrada_status_utc"] if delivery else None,
                       situacao_ciclo_precificacao=state,
                       motivos_ciclo_precificacao_json=json.dumps(sorted(reasons)))
        if not approved:
            return
        work = useful = pause = pause_useful = 0.0
        for r in chain:
            left, right = time(r["entrada_status_utc"]), time(r["saida_status_utc"])
            hours = (right - left).total_seconds() / 3600
            business = calendar.hours(left, right)
            if role(r) == "pausa":
                pause += hours
                pause_useful += business
            else:
                work += hours
                useful += business
                result[r["interval_id"]].update(
                    contribuicao_precificacao_horas_corridas=round(hours, 3),
                    contribuicao_precificacao_horas_uteis=round(business, 3))
        result[delivery["interval_id"]].update(
            entrega_precificacao_observada=True,
            precificacao_horas_corridas=round(work, 3),
            precificacao_horas_uteis=round(useful, 3),
            pausas_precificacao_horas_corridas=round(pause, 3),
            pausas_precificacao_horas_uteis=round(pause_useful, 3),
            janela_precificacao_horas_corridas=round((end - start).total_seconds() / 3600, 3))

    for group in groups.values():
        ordered = sorted(group, key=lambda r: (time(r["entrada_status_utc"]), r["interval_id"]))
        chain, reasons = [], set()
        for row in ordered:
            kind = role(row)
            if kind == "inicio":
                close(chain, "reiniciado_sem_entrega", reasons | {"nova_entrada_antes_da_entrega"})
                chain, reasons = [], set()
            if chain:
                prev = chain[-1]
                if time(prev["saida_status_utc"]) != time(row["entrada_status_utc"]):
                    reasons.add("lacuna_ou_sobreposicao")
                if time(row["entrada_status_utc"]) <= time(prev["entrada_status_utc"]):
                    reasons.add("ordem_ambigua")
            if kind == "entrega":
                source = json.loads(row.get("registro_origem_json", "{}"))
                if row["ambiente_origem"] == "viu2":
                    if source.get("qualidade_rotulo") not in {
                        "label_observed_at_start", "label_observed_at_exit_previous_value"
                    }:
                        reasons.add("marco_entrega_sem_rotulo_aprovado")
                elif source.get("qualidade_historico") != "observed":
                    reasons.add("marco_entrega_nao_observado")
                close(chain, "entregue_observado", reasons, row)
                chain, reasons = [], set()
                continue
            if kind == "terminal_sem_entrega":
                if chain:
                    chain.append(row)
                    close(chain, "encerrado_sem_entrega", reasons)
                chain, reasons = [], set()
                continue
            if not chain and kind != "inicio":
                continue
            chain.append(row)
            if kind == "nao_mapeado":
                reasons.add("status_nao_mapeado")
            left, right = time(row["entrada_status_utc"]), time(row["saida_status_utc"])
            if right is None or right < left or row.get("elegivel_comparacao") is not True:
                reasons.add("intervalo_sem_evidencia_aprovada")
            if row.get("versao_calendario_origem") != calendar.version:
                reasons.add("calendario_divergente")
        close(chain, "em_aberto", reasons)
    return result
