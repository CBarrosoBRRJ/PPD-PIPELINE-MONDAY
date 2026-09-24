# Recibo da execução automática — 24/09/2026

## Atualização posterior: v13 executada, homologação pendente

Esta seção prevalece sobre o recibo v12 abaixo. Evidências enviadas pelo operador:

- Build `2bdee745-33c7-47f7-81b5-870a39c8d3aa` concluído; imagem
  `us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday@sha256:997bdd841acd4949a620af3d0ea163c199ecf6941356c86e4cd128b9f73cd412`.
- Ensaio `pipeline-monday-7k69k`: backlog 4.853 registros e talentos 41,
  ambos validados, sem publicação. Falha ValueError do primeiro ensaio não
  reproduzida; causa não comprovada.
- Controle migrado de v7 para `sla-consolidado-precificacao-v8`, geração
  `1790283201855955` (geração da migração, não necessariamente a atual).
- Primeira execução diária v13 `pipeline-monday-vpwfp` falhou nos snapshots
  com Forbidden; consolidada bloqueada. Alerta retornou `not_configured`.
- Operador adicionou binding `pipeline_snapshots_v13`, objectAdmin para a conta
  `pipeline-orcamento@gglobo-viu-dados-hdg-prd.iam.gserviceaccount.com`, limitado
  aos prefixos `snapshots/monday_backlog_agenciamento_2026/` e
  `snapshots/monday_talentos_exclusivos/` no bucket dedicado. Expressão exata,
  conta e papel foram conferidos; prefixos sem objetos antes da nova tentativa.
- Execução `pipeline-monday-2h8lf` concluída: backlog 4.860 linhas, talentos 41,
  consolidada 9.672 passagens / 2.209 projetos, todos publication_verified=true;
  SLA Globocorp skipped com publicação verificada no corte 24/09 03:00 UTC.
- Orquestração 21:07:03.499117Z até 21:11:51.518554Z, aproximadamente 4min48s,
  sem contabilizar todo o provisionamento. Recibo não explica o custo por operação.

Agenda permanece pausada conforme último estado informado; não há recibo de
retomada. Validação independente dos novos campos, regras de precificação,
controles GCS sem pending e alerta externo ainda pendentes. Não declarar entrega
completa. Consulta de auditoria: `tabelas/monday_sla_orcamento/sql/auditoria_cadastro_atual.sql`.
Legenda: `docs/LEGENDA_CADASTRO_SLA.md`. Alterações locais posteriores de consulta,
testes e documentação não modificam a imagem v13 implantada.

## Histórico: execução automática v12

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
