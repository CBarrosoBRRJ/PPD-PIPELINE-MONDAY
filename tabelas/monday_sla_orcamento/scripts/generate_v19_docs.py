"""Gera docs/CONTRATO_MODELO_V19.md a partir do contrato executável (não editar o .md à mão)."""

from pathlib import Path

from monday_sla_orcamento.modelo_v19 import CLUSTERING, CONTRACTS, KEYS, PARTITION_MONTH, RULE

QUESTIONS = {
    "monday_sla_projeto": "Quanto tempo levamos para orçar e entregar cada projeto?",
    "monday_sla_ciclo": "Como foi cada entrega e cada retrabalho?",
    "monday_sla_passagem": "Base comum: cada passagem por status, com origem da duração.",
    "monday_sla_tempo_status": "Quanto tempo cada projeto ficou em cada status?",
    "monday_sla_resposta_cliente": "Quanto o cliente demora para responder, e o que ele fez?",
    "monday_sla_em_andamento": "O que está aberto agora, há quanto tempo, e com qual alerta?",
    "monday_sla_referencia_status": "Qual o tempo de referência (SLA) de cada status?",
    "monday_sla_gargalo_mensal": "Onde o tempo se acumula, mês a mês?",
    "monday_sla_kpi_mensal": "Como estamos no mês (visão executiva)?",
    "monday_sla_qualidade": "Quem ficou fora do cálculo, e por quê?",
    "monday_sla_erro_preenchimento": "Quais erros de preenchimento aconteceram (uma linha por erro)?",
    "monday_sla_qualidade_preenchimento": "Como está o preenchimento por mês e por responsável?",
    "monday_dim_status": "Quais status existem, como contam e quanto são usados?",
    "monday_dim_calendario": "Quais dias são úteis e quantas horas úteis cada um tem?",
    "monday_sla_projeto_diario": "Como cada projeto evoluiu dia a dia (base de previsão/ML)?",
    "monday_sla_item_duplicado": "Quais itens foram duplicados de outro orçamento (fora do SLA, para estudo)?",
    "monday_sla_standby": "Quais projetos estão parados em Standby agora, e há quanto tempo?",
    "monday_sla_projeto_pool": "Quanto tempo levam os projetos com squad ou vários talentos (pool, fora do SLA oficial)?",
    "monday_sla_sem_entrada": "Quais projetos não começaram por Entrada, e qual foi a trajetória completa de cada um?",
    "monday_dim_talento": "Quais talentos aparecem no quadro, com que grafias, se são exclusivos e quantas vezes foram usados?",
    "monday_dim_marca": "Quais marcas aparecem no quadro, com que grafias e quantas vezes foram usadas?",
}

NOTES = {
    "monday_sla_kpi_mensal": (
        "**Leitura das medidas de tempo:** `tempo_orcamento_p50_horas_uteis` e `tempo_orcamento_p80_horas_uteis` "
        "medem o trabalho **até a 1ª entrega** dos projetos que tiveram a 1ª entrega naquele mês, sem os ajustes "
        "posteriores. O tempo total com retrabalho está em `monday_sla_projeto.tempo_orcamento_horas_uteis`. "
        "Decisão de 29/09/2026: manter a medida mensal como tempo até a 1ª entrega."),
}


def render():
    lines = [f"# Contrato do modelo v19 (`{RULE}`)", "",
             "Gerado por `scripts/generate_v19_docs.py`. Regras de negócio: nota do projeto (R1–R26) e",
             "`src/monday_sla_orcamento/modelo_v19.py`. Horas úteis: seg–sex, 10–13h e 14–19h, America/Sao_Paulo.", ""]
    for name, fields in CONTRACTS.items():
        extras = []
        if name in PARTITION_MONTH:
            extras.append(f"partição mensal por `{PARTITION_MONTH[name]}`")
        if name in CLUSTERING:
            extras.append("cluster " + ", ".join(f"`{c}`" for c in CLUSTERING[name]))
        lines += [f"## `{name}`", "", f"**Pergunta:** {QUESTIONS[name]}", "",
                  f"**Chave:** {', '.join(f'`{k}`' for k in KEYS[name])}" + (f" · {'; '.join(extras)}" if extras else ""),
                  "", "| Coluna | Tipo | Obrigatória |", "| :--- | :--- | :-: |"]
        lines += [f"| `{k}` | {t} | {'sim' if required else ''} |" for k, (t, required) in fields.items()]
        lines.append("")
        if name in NOTES:
            lines += [NOTES[name], ""]
    return "\n".join(lines)


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[1] / "docs" / "CONTRATO_MODELO_V19.md"
    target.write_text(render(), encoding="utf-8", newline="\n")
    print(target)
