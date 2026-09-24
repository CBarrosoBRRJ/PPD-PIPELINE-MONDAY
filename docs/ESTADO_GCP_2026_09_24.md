# Recibo da execução automática — 24/09/2026

Fonte: saídas de Cloud Shell enviadas pelo operador em 24/09. Este documento
atualiza o estado operacional descrito em `ESTADO_GCP_2026_09_23.md`; aquele
arquivo permanece como histórico. Não houve alteração de configuração GCP aqui.

## Execução e publicação

- Execução `pipeline-monday-p59rf`: início `2026-09-24T09:00:13.030644Z`, fim
  `2026-09-24T09:08:55.465960Z`, uma tarefa concluída, sem falha informada.
- `orchestration_end` às `09:08:52.116522Z`: `status=success`.
- Produto `sla_orcamento`: `status=success`, `publication_verified=true`,
  corte `2026-09-24T03:00:00Z`, 3.736 passagens e 2.486 projetos na Gold da
  origem nova; `run_id=79cab97c-4fcf-598a-9b60-dfe834617f96`.
- Produto `monday_sla_orcamento`: `status=success`, `publication_verified=true`,
  corte `2026-09-24T03:00:00Z`, 9.672 passagens e 2.209 projetos.
- Consulta BigQuery sem cache confirmou contrato `sla-consolidado-analise-v7`,
  corte `2026-09-24 03:00:00`, 9.672 passagens, 2.209 projetos, 6.227 passagens
  com `sla_etapa_horas_uteis` e 215 com `origem_duracao_analise="estimada"`.

A hora de início coincide com a agenda conhecida de 06h em São Paulo. As saídas
enviadas não incluem o registro `AttemptFinished` do Scheduler para este dia;
portanto a atribuição do disparo ao Scheduler é fortemente indicada pelo horário,
mas não foi comprovada diretamente por esse log. A execução e a publicação diária
estão comprovadas pelos recibos acima.

## Comparação com 23/09

| Medida consolidada | 23/09 | 24/09 | Diferença |
|---|---:|---:|---:|
| Passagens | 9.648 | 9.672 | +24 |
| Projetos | 2.209 | 2.209 | 0 |
| Durações observadas para KPI de etapa | 6.227 | 6.227 | 0 |
| Durações estimadas | 191 | 215 | +24 |

A coincidência dos dois incrementos não prova, por si, que as 24 linhas novas
são exatamente as 24 novas estimativas. Pode haver entradas, saídas ou
reclassificações compensatórias; uma comparação por `interval_id` entre os dois
cortes é necessária para afirmar a composição da mudança. Caso as três classes
de duração sejam exaustivas e mutuamente exclusivas, a quantidade indisponível
inferida no corte atual é 3.230 (= 9.672 − 6.227 − 215). Ainda não foi consultada
diretamente neste corte.

## Uso e próximos controles

O KPI observado por etapa segue disponível no escopo aprovado: 6.227 passagens.
As 215 estimativas são análise com proveniência, não duração observada nem rótulo
de treinamento. A execução automática não homologa o KPI global entre o primeiro
status e uma entrega comercial: o marco de entrega, o ciclo, as reaberturas e a
cobertura ainda exigem contrato de negócio.

Antes de publicar o dashboard, reconciliar as classes de duração por origem e
avaliar amostra das alterações entre cortes. Ver
`tabelas/monday_sla_orcamento/sql/auditoria_diaria_dashboard.sql` para as
consultas somente leitura. Os arquivos congelados ViU2 e os controles GCS
continuam necessários; não mudar retenção a partir deste recibo.
