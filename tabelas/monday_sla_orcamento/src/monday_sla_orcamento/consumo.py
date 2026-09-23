"""Consumer projection: safe KPI measure plus evidence-specific row labels."""

import json

from monday_sla_orcamento.kpi_etapa import decision

FIELDS = {
    "sla_etapa_horas_uteis": ("FLOAT", False),
    "classificacao_consumo": ("STRING", True),
    "motivos_inelegibilidade_kpi_json": ("STRING", True),
    "versao_regra_kpi": ("STRING", True),
}


def project(row, calendar):
    verdict = decision(row, calendar)
    eligible = verdict["elegivel_kpi_etapa_candidato"]
    if eligible:
        category = "aprovado_kpi_etapa"
    elif row.get("status_terminal") is True:
        category = "encerramento_observado"
    elif (row.get("status_terminal") is False
          and row.get("situacao_sla_registro") == "sem_saida_observada_nao_comprova_abandono"):
        # Historical absence of exit is NOT evidence of currently ongoing work.
        category = "sem_saida_observada"
    else:
        category = "evidencia_insuficiente"
    return {
        "sla_etapa_horas_uteis": row["duracao_horas_uteis"] if eligible else None,
        "classificacao_consumo": category,
        "motivos_inelegibilidade_kpi_json": json.dumps(verdict["motivos"], ensure_ascii=False),
        "versao_regra_kpi": verdict["politica"],
    }
