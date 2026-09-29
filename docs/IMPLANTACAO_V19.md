# Implantação em produção — v19 (28/09/2026)

Objetivo: colocar a v19 em produção como **publicação única**, com as regras e as 17 tabelas
novas, e **apagar as 4 tabelas da v18**, com backup. Inclui todas as correções de estabilidade
([v18.1](IMPLANTACAO_V18_1_ESTABILIDADE.md)).

| Fica (fontes e outros produtos) | Sai (v18, depois do backup) | Entra (v19) |
| :--- | :--- | :--- |
| `monday_sla_orcamento_globocorp`, `monday_sla_orcamento_viu2`, `monday_log_viu2`, `monday_backlog_agenciamento_2026`, `monday_talentos_exclusivos` | `monday_sla_orcamento`, `monday_ciclos_orcamento`, `monday_fila_precificacao`, `monday_sla_baixa_qualidade_de_dado` | as 17 tabelas de [CONTRATO_MODELO_V19.md](../tabelas/monday_sla_orcamento/docs/CONTRATO_MODELO_V19.md) |

**Quem usa as tabelas que saem.** Consulta ao histórico do BigQuery em 28/09, cobrindo 30 dias:
- só `caio.barroso@viu.com.br` e o próprio pipeline;
- nenhuma view depende delas.

**Ensaio com dados reais de produção.** Corte de 28/09, feito localmente com os mesmos insumos do job:
- **1.785 projetos**: 1.294 só da ViU2, 289 que atravessaram a migração e 202 nascidos na Globocorp;
- tempo de orçamento com mediana de 10 h úteis;
- 18 itens duplicados, fora do SLA;
- 90 projetos em Standby;
- em andamento, 64 críticos e 95 em atenção;
- a etapa v19 levou ~75 s e usou 62 MB.

Pacote: `runtime/pipeline-monday-release-20260928-v19-final.zip`. Confira o SHA256 no passo 1.
Imagem atual, para voltar atrás: `…/pipeline-monday@sha256:dd3ab2619c6e489ca084562e81a947f4e8ac8b723f2b30bfd549071435e88a65`.

## Passo a passo (Caio executa no Cloud Shell)

Faça fora da janela das 05:30 às 07:00. Se um passo não der o resultado esperado, **pare** e não siga para o próximo.

**1. Enviar o pacote e conferir o hash.** O resultado tem de ser o valor registrado em `docs/IMPLANTACAO_V19.md`, na seção "Hash do pacote".
```bash
sha256sum pipeline-monday-release-20260928-v19-final.zip
```

**2. Gerar a imagem e anotar o digest.** O `sha256:…` impresso é o `DIGEST` dos passos seguintes.
```bash
rm -rf release-v19 && mkdir release-v19 && unzip -q pipeline-monday-release-20260928-v19-final.zip -d release-v19 && cd release-v19
gcloud builds submit . --project=gglobo-viu-dados-hdg-prd \
  --tag=us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday:v19
gcloud artifacts docker images describe \
  us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday:v19 --format='value(image_summary.digest)'
```

**3. Pausar a agenda deste pipeline** e confirmar que nada está rodando:
```bash
gcloud scheduler jobs pause pipeline-monday-diario --project=gglobo-viu-dados-hdg-prd --location=us-central1
gcloud run jobs executions list --job=pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 --limit=3
```

**4. Trocar a imagem e criar as 17 tabelas v19** (vazias, com o schema do contrato):
```bash
gcloud run jobs update pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 \
  --image=us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday@DIGEST \
  --args=initialize-v19,--manifest,/app/pipelines.json,--writers-stopped
gcloud run jobs execute pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 --wait
```
Esperado no log: `status: modelo_v19_inicializado` e `tabelas: 17`.

**5. Publicar a primeira v19.** Nesta execução a v18 ainda é publicada junto:
```bash
gcloud run jobs update pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 \
  --args=daily,--manifest,/app/pipelines.json
gcloud run jobs execute pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 --wait
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="pipeline-monday" AND jsonPayload.event="consolidated_publication_confirmed"' \
  --project=gglobo-viu-dados-hdg-prd --order=desc --limit=1 --format='json(jsonPayload.modelo_v19)'
```
Esperado: `modelo_v19.status: success` e `publication_verified: true`.

**6. Conferir a v19 no BigQuery.** Os números devem ficar próximos aos do ensaio:
```sql
SELECT situacao_atual, COUNT(*) projetos, APPROX_QUANTILES(tempo_orcamento_horas_uteis, 2)[OFFSET(1)] mediana_h
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_projeto` GROUP BY 1 ORDER BY 2 DESC;
SELECT status_nome, passagens_total, itens_total, no_quadro_atual
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_dim_status` ORDER BY passagens_total DESC;
```

**7. Aposentar a v18 no pipeline.** Daqui em diante o job publica **só a v19** e não toca mais nas tabelas antigas:
```bash
gcloud run jobs update pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 \
  --args=retire-v18,--manifest,/app/pipelines.json,--writers-stopped
gcloud run jobs execute pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 --wait
gcloud run jobs update pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 \
  --args=daily,--manifest,/app/pipelines.json
```
Esperado no log: `status: v18_aposentada`.

**8. Fazer o backup das 4 tabelas v18 no GCS**, em formato Avro, que guarda schema e tipos:
```bash
for t in monday_sla_orcamento monday_ciclos_orcamento monday_fila_precificacao monday_sla_baixa_qualidade_de_dado; do
  bq extract --location=US --destination_format=AVRO --use_avro_logical_types \
    "gglobo-viu-dados-hdg-prd:viu_agenciamento.$t" \
    "gs://gglobo-viu-dados-hdg-prd-ppd-pipeline-monday/backups/v18_20260928/$t/part-*.avro"
done
gcloud storage ls -l -r gs://gglobo-viu-dados-hdg-prd-ppd-pipeline-monday/backups/v18_20260928/
```
Esperado: arquivos `.avro` para as 4 tabelas. Anote as contagens de linhas, para conferir se um dia precisar restaurar:
```bash
bq query --use_legacy_sql=false 'SELECT "sla" t, COUNT(*) n FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento` UNION ALL SELECT "ciclos", COUNT(*) FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento` UNION ALL SELECT "fila", COUNT(*) FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_fila_precificacao` UNION ALL SELECT "qualidade", COUNT(*) FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_baixa_qualidade_de_dado`'
```

**9. Apagar as 4 tabelas v18.** Só depois dos passos 7 e 8 conferidos. A exclusão é irreversível no BigQuery; o backup do passo 8 é a garantia.
```bash
for t in monday_sla_orcamento monday_ciclos_orcamento monday_fila_precificacao monday_sla_baixa_qualidade_de_dado; do
  bq rm -f -t "gglobo-viu-dados-hdg-prd:viu_agenciamento.$t"
done
bq ls --max_results=100 gglobo-viu-dados-hdg-prd:viu_agenciamento | grep monday_
```
Esperado: ficam as 5 fontes e as 17 tabelas v19.

**10. Rodar de novo, já só com a v19, e retomar a agenda:**
```bash
gcloud run jobs execute pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 --wait
gcloud scheduler jobs resume pipeline-monday-diario --project=gglobo-viu-dados-hdg-prd --location=us-central1
```
Esperado: `orchestration_end` com `status: success`.

**11. Segurança e alerta.** Os comandos estão em [IMPLANTACAO_V18_1_ESTABILIDADE.md](IMPLANTACAO_V18_1_ESTABILIDADE.md):
- remover o `run.developer` da conta de deploy;
- criar o alerta "25 h sem sucesso".

## Se algo falhar

| Onde | O que fazer |
| :--- | :--- |
| Passos 1–5 | Volte a imagem anterior: passo 4 com o digest `dd3ab261…` e os argumentos `daily,--manifest,/app/pipelines.json`. As tabelas v19 podem ficar; a v18 segue normal |
| Passo 7 em diante | Não volte a imagem anterior: ela espera as tabelas v18. Mantenha a v19 e me chame |
| Restaurar uma tabela v18 | `bq load --source_format=AVRO --use_avro_logical_types viu_agenciamento.<tabela> "gs://…/backups/v18_20260928/<tabela>/part-*.avro"` |

Nunca apague travas, journals ou o bucket para "destravar".

## Hash do pacote

`pipeline-monday-release-20260928-v19-final.zip`: 110 arquivos, SHA256
`27ddb1a30163c375271b9bd43aad61fd415029f4149983ca1ef9081fa5b1e28b` (648 testes aprovados).

## Recibo de produção — 28/09/2026 (conferido por consulta de leitura)

| Passo | Evidência |
| :--- | :--- |
| Pacote | SHA256 `27ddb1a3…` conferido no Cloud Shell |
| Build | `95ad73dd-df67-45ce-8ccc-c0ccd1ca63e7` SUCCESS · imagem `pipeline-monday@sha256:34a629d406d9826b91a756143d615bd0112f6cfae2991c7be5bcf2b535794885` |
| `initialize-v19` | execução `pipeline-monday-wc77v`: 17 tabelas criadas às 21:45 UTC |
| Primeira publicação v19 | execução `pipeline-monday-7kmxw`: `success`; 1.785 projetos, 1.887 ciclos, 8.606 passagens (iguais ao ensaio); controle sem pendência |
| `retire-v18` | execução `pipeline-monday-pnzp8`: `v18_aposentada: true`; job de volta em `daily` |
| Backup v18 | `gs://…-ppd-pipeline-monday/backups/v18_20260928/`, 8 arquivos Avro; contagem conferida registro a registro: 7.693 · 1.685 · 4 · 1.636 |
| Exclusão v18 | `monday_sla_orcamento`, `monday_ciclos_orcamento`, `monday_fila_precificacao`, `monday_sla_baixa_qualidade_de_dado` |
| Execução só v19 | `pipeline-monday-wcvjr`: `success`, v19 publicada e verificada (1.785 projetos) |
| Agenda | `pipeline-monday-diario` ENABLED, `0 6 * * *`, America/Sao_Paulo |
| Segurança | `roles/run.developer` removido da conta `deploy-sla-orcamento`; ficou só `serviceUsageConsumer` |
| Alerta | métrica `pipeline_monday_sucesso` e política `alertPolicies/15463508235751031085` ("nenhuma execução com sucesso em 25h"), com aviso por e-mail para caio.barroso@viu.com.br |

**Primeira execução automática (29/09/2026):** `pipeline-monday-w5gsw`, 06:00–06:11 BRT, sucesso e sem
erros no log; 17 tabelas com o corte de 29/09; 1.791 projetos, 1.512 entregas, 8.632 passagens; estado
compactado com 5,7 MB. Pendência: depois de 7 dias estáveis, avaliar baixar a memória do job para 4 GB.

## Atualização v19-2 — regra `modelo-v19-2` (29/09/2026)

Troca só a imagem. Agenda, argumentos (`daily`), bucket, permissões, alerta e esquema das 17 tabelas
ficam iguais; o próprio job regrava as tabelas na execução seguinte. O controle no GCS continua com
a identidade `modelo-v19-1` (contrato), por isso a imagem nova publica sem migração, e a anterior
continua compatível para voltar atrás.

**O que muda** (revisão técnica em [REVISAO_TECNICA_V19_2026_09_28.md](REVISAO_TECNICA_V19_2026_09_28.md)):
- pausa, Retorno Marca ou status vazio depois da entrega não abre retrabalho; sem ação posterior, o desfecho é `pausado`;
- série diária de projetos em Standby vai até o corte; o dia tem fim exclusivo (evento às 00:00 conta no dia seguinte);
- duplicado só é ligado a um original único; senão fica em branco com o erro `duplicado_original_ambiguo`;
- validação mais rígida antes de publicar (um corte só, sem durações negativas, retrabalhos batendo com os ciclos);
- inicialização retomável; `job_retry=None` nas consultas com `job_id` fixo (aviso do cliente BigQuery).

**Comparação com os dados de 29/09** (mesmas 8.632 passagens, núcleo v19-1 × v19-2):
- pediu ajuste 101 → 98 (2 `pausado`, 1 nova entrega sem ajuste);
- ciclos de retrabalho 101 → 98 (IDs de ciclo preservados: 1.889 de 1.889);
- série diária 51.990 → 60.434 linhas (os 90 projetos em Standby vão até o corte);
- mediana do tempo de orçamento igual (10,02 h);
- referência de Aguardando Feedback: atenção 54,6 → 48,5 h e crítico 119 → 107 h, com 24 projetos subindo de nível de alerta.

**Pacote:** `runtime/pipeline-monday-release-20260929-v19-2.zip`, 110 arquivos, SHA256
`b59fb1f3dffb4220113d1453c4e406d9f1fc10e4ef775ba4de8a41e25eceac0b` (657 testes aprovados).
**Voltar atrás:** passo 3 com o digest anterior `sha256:34a629d406d9826b91a756143d615bd0112f6cfae2991c7be5bcf2b535794885`.

Passos no Cloud Shell, fora da janela das 05:30 às 07:00:

**1. Enviar o pacote** (menu ⋮ → Upload) e conferir o hash:
```bash
sha256sum pipeline-monday-release-20260929-v19-2.zip
```

**2. Gerar a imagem e anotar o digest:**
```bash
rm -rf release-v19-2 && mkdir release-v19-2 && unzip -q pipeline-monday-release-20260929-v19-2.zip -d release-v19-2 && cd release-v19-2
gcloud builds submit . --project=gglobo-viu-dados-hdg-prd   --tag=us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday:v19-2
gcloud artifacts docker images describe   us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday:v19-2 --format='value(image_summary.digest)'
```

**3. Trocar só a imagem** (sem mudar argumentos):
```bash
gcloud run jobs update pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1   --image=us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday@DIGEST
```

**4. Rodar uma vez e conferir:**
```bash
gcloud run jobs execute pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 --wait
bq query --use_legacy_sql=false 'SELECT versao_regra, COUNT(*) n FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_projeto` GROUP BY 1'
```
Esperado: execução com sucesso e `versao_regra = modelo-v19-2`.

### Recibo da v19-2 — 29/09/2026 (conferido por consulta de leitura)

| Passo | Evidência |
| :--- | :--- |
| Pacote | SHA256 `b59fb1f3…` conferido no Cloud Shell |
| Build | `b6b3fdf4-e5d5-4057-a551-ff2e1458eb3e` SUCCESS · imagem `pipeline-monday@sha256:4f5efb2312cb52779c923ef18bf94dd701be7f0a304aee687b3b530ceaa0d855` |
| Troca de imagem | job `pipeline-monday` atualizado; argumentos `daily` mantidos |
| Execução | `pipeline-monday-trh49`: sucesso, sem avisos nem erros no log (inclusive sem o `FutureWarning` do BigQuery) |
| BigQuery | `versao_regra = modelo-v19-2`; corte 29/09; 1.791 projetos; 99 pediu ajuste e 2 `pausado`; 99 ciclos de retrabalho; 60.434 linhas na série diária; referência de atenção de Aguardando Feedback 48,5 h; alertas: 94 críticos, 92 em atenção, 67 ok |

A diferença de 1 caso entre a comparação local (98) e a produção (99) já existia na v19-1: o ensaio local
partiu das passagens exportadas com horário truncado em segundos. A variação produzida pela regra é a mesma (−3).

Voltar atrás, se necessário: passo 3 com `sha256:34a629d406d9826b91a756143d615bd0112f6cfae2991c7be5bcf2b535794885`.

## Atualização v19-3 — regras de talento R21–R26 e rastreabilidade total (29/09/2026)

**Por quê.** A análise de cobertura mostrou 35,8% do quadro na análise. A maior perda vinha do filtro da Globocorp
(`quarentena_projeto` no estado): 1.620 itens retidos só por `talento_identidade_pendente` (talento em Interveniência
sem revisão de nome no catálogo; nenhum nome tinha sido revisado). Também havia 386 itens do quadro sem registro em
nenhuma tabela do modelo.

**Regras de negócio (decididas em 29/09/2026):**
- R21: Talentos Exclusivos e Interveniência viram um só talento (`talento` + `eh_interveniencia`).
- R22: mesmo talento nas duas colunas vale (comparação sem acento, caixa ou espaços).
- R23: talentos diferentes nas duas colunas → erro, fora do SLA (`talento_ambas_colunas`, gravidade erro).
- R24: as duas vazias → erro, fora do SLA (`talento_nao_informado`).
- R25: squad ou mais de um talento → pool, fora do SLA, para análise própria (`talento_squad`, `talento_multiplo`).
- R26: revisão de nome no catálogo não retém mais o projeto (a revisão fica para análises por talento).

**Código.**
- Filtro da Globocorp `RULE_VERSION 2.3.0` (`rules/eligibility.py`): sem `talento_identidade_pendente`; `talento_ambas_colunas` só com nomes diferentes; `talent_policy` registrada no snapshot de regras.
- Consolidação (`talent_context.py`, `talento-canal-unico-v2`): mesmas regras.
- Modelo `modelo-v19-3`: todo item do quadro que não está em outra tabela entra em `monday_sla_qualidade` com o motivo real (título, input, talento); sem motivo, `sem_historico_de_status`. Descrições e gravidades dos erros de talento atualizadas.
- Esquema e contrato inalterados (`modelo-v19-1`). 662 testes aprovados.

**Efeito estimado (quarentena de 29/09):** 1.620 itens liberados. ~561 do histórico da ViU2 que começam por Entrada e
até 250 pedidos novos entram no SLA; ~809 da ViU2 sem Entrada comprovada vão para a qualidade com o motivo certo.
Cobertura esperada de ~52% do quadro. Continuam retidos 860 itens por regra de escopo real.

**Pacote:** `runtime/pipeline-monday-release-20260929-v19-3.zip`, 110 arquivos, SHA256 `ffe9c049695f7cbe712a02cd9b772edc46345364a5dea91f966aeffceac22a49`.
Passos iguais aos da v19-2, com a tag `pipeline-monday:v19-3`. Para voltar atrás: digest da v19-2 (`sha256:4f5efb23…`).

**Conferência esperada:**
```sql
SELECT ANY_VALUE(versao_regra) regra, COUNT(*) projetos FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_projeto`;
SELECT situacao_calculo, motivos_json, COUNT(*) FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_qualidade` GROUP BY 1, 2 ORDER BY 3 DESC;
```
Esperado: `modelo-v19-3`, cerca de 2.600 projetos e nenhum `sem_item_na_gold_atual` causado por talento pendente.
