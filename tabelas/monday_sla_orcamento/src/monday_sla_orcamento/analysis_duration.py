"""Unified analytical measure with explicit provenance; official KPI unchanged."""

VERSION = "duracao-analise-v1"
FIELDS = {
    "duracao_analise_horas": ("FLOAT", False),
    "duracao_analise_horas_uteis": ("FLOAT", False),
    "origem_duracao_analise": ("STRING", True),
    "versao_regra_duracao_analise": ("STRING", True),
}


def project(row):
    hours = working = None
    origin = "indisponivel"
    if row["status_terminal"] is False:
        if row["elegivel_comparacao"] is True and row["sla_etapa_horas_uteis"] is not None:
            hours, working = row["duracao_horas"], row["sla_etapa_horas_uteis"]
            origin = "observada_validada"
        elif (row["saida_status_utc"] is None and row["saida_estimada_utc"] is not None
              and row["metodo_estimativa"] == "estimada_pela_proxima_etapa_entre_ambientes"
              and row["duracao_estimada_horas"] is not None
              and row["duracao_estimada_horas_uteis"] is not None):
            hours, working = row["duracao_estimada_horas"], row["duracao_estimada_horas_uteis"]
            origin = "estimada"
    return {"duracao_analise_horas": hours, "duracao_analise_horas_uteis": working,
            "origem_duracao_analise": origin, "versao_regra_duracao_analise": VERSION}
