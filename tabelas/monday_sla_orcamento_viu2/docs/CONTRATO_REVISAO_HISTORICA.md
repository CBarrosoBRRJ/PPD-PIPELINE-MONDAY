# Contrato privado de revisão histórica

Versão: `sla-viu2-review-v1`.

Gerado de review_contract.py. Não é o contrato implantado no BigQuery.

Origem: resgate viu2; grão: passagem observada por conta/quadro/item/status/início.
Chave interval_id UUIDv5 com namespace de revisão; não substitui IDs/SKs de produção.
Consumidor: homologação técnica. Falha bloqueia a exportação inteira; saídas existentes não são sobrescritas.
Durações desconhecidas e nomes ausentes são NULL. Horário local: America/Sao_Paulo.
Marca/Talento originais são cadastro na coleta, não entidades revisadas ou atributos históricos.
Nenhuma linha é aprovada para KPI; projeto_id permanece NULL, sem união automática por nome.

| Campo | Tipo | Obrigatório |
|---|---|---|
| ordem_etapa | INTEGER | Sim |
| projeto_nome | STRING | Não |
| status_nome | STRING | Não |
| entrada_status_local | DATETIME | Sim |
| saida_status_local | DATETIME | Não |
| duracao_horas | FLOAT | Não |
| duracao_horas_uteis | FLOAT | Não |
| marca_original | STRING | Não |
| talento_original | STRING | Não |
| conta_origem | STRING | Sim |
| ambiente_origem | STRING | Sim |
| board_id | INTEGER | Sim |
| item_id | INTEGER | Sim |
| interval_id | STRING | Sim |
| projeto_id | STRING | Não |
| status_index | STRING | Sim |
| situacao_passagem | STRING | Sim |
| entrada_status_utc | TIMESTAMP | Sim |
| saida_status_utc | TIMESTAMP | Não |
| cadastro_referencia_utc | TIMESTAMP | Não |
| origem_atributos | STRING | Sim |
| qualidade_rotulo | STRING | Sim |
| retorno_observado | BOOLEAN | Sim |
| elegivel_comparacao | BOOLEAN | Sim |
| validacao_negocio | STRING | Sim |
| versao_contrato | STRING | Sim |
| versao_calendario | STRING | Sim |
| eventos_suporte_json | STRING | Sim |
| eventos_saida_json | STRING | Sim |
| pendencias_json | STRING | Sim |

## Situações

- observed_closed_candidate: saída observada, horas corridas/úteis reconciliadas.
- no_observed_exit: entrada conhecida; saída e durações NULL, sem extensão até hoje.
- interrupted_by_evidence_gap: entrada conhecida, mas lacuna impede determinar saída/duração.

Retorno observado não certifica todos os retornos possíveis. Ausência de pendência de lote não prova completude.
validacao_negocio=pendente e elegivel_comparacao=false são invariantes desta versão.
As regras públicas atuais de exclusão, entidades, responsabilidade e métricas totais ainda não estão aplicadas.
Revisão posterior deve migrar contrato e consumidores explicitamente; não enfraquecer validate_public da versão corrente.
