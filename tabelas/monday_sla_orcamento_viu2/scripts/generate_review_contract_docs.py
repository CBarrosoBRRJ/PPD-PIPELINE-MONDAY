"""Generate private-review schema reference, not production DDL."""

import json
from pathlib import Path

from historico_viu2.review_contract import FIELDS, VERSION, schema


def main():
    root = Path(__file__).resolve().parents[1]
    lines = ["# Contrato privado de revisão histórica", "", f"Versão: `{VERSION}`.", "",
             "Gerado de review_contract.py. Não é o contrato implantado no BigQuery.", "",
             "Origem: resgate viu2; grão: passagem observada por conta/quadro/item/status/início.",
             "Chave interval_id UUIDv5 com namespace de revisão; não substitui IDs/SKs de produção.",
             "Consumidor: homologação técnica. Falha bloqueia a exportação inteira; saídas existentes não são sobrescritas.",
             "Durações desconhecidas e nomes ausentes são NULL. Horário local: America/Sao_Paulo.",
             "Marca/Talento originais são cadastro na coleta, não entidades revisadas ou atributos históricos.",
             "Nenhuma linha é aprovada para KPI; projeto_id permanece NULL, sem união automática por nome.", "",
             "| Campo | Tipo | Obrigatório |", "|---|---|---|"]
    for name, (kind, required) in FIELDS.items():
        lines.append(f"| {name} | {kind} | {'Sim' if required else 'Não'} |")
    lines += ["", "## Situações", "",
              "- observed_closed_candidate: saída observada, horas corridas/úteis reconciliadas.",
              "- no_observed_exit: entrada conhecida; saída e durações NULL, sem extensão até hoje.",
              "- interrupted_by_evidence_gap: entrada conhecida, mas lacuna impede determinar saída/duração.",
              "", "Retorno observado não certifica todos os retornos possíveis. Ausência de pendência de lote não prova completude.",
              "validacao_negocio=pendente e elegivel_comparacao=false são invariantes desta versão.",
              "As regras públicas atuais de exclusão, entidades, responsabilidade e métricas totais ainda não estão aplicadas.",
              "Revisão posterior deve migrar contrato e consumidores explicitamente; não enfraquecer validate_public da versão corrente."]
    (root / "docs/CONTRATO_REVISAO_HISTORICA.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (root / "docs/review_schema.json").write_text(json.dumps(schema(), indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
