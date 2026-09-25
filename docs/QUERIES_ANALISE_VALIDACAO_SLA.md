# Queries copiaveis — analise e validacao de SLA

GoogleSQL / BigQuery, localizacao US. Executar uma consulta por vez no editor.
Somente SELECT: nenhuma altera dados. Consultas conferidas com os contratos
locais, mas nao executadas no GCP nesta revisao. No CLI usar use_legacy_sql=false,
use_cache=false e maximum_bytes_billed=1073741824 (1 GiB); se exceder, investigar
antes de aumentar. Em execucao diaria concorrente, repetir se contagens mudarem.

Tabela de consumo: monday_sla_orcamento, uma linha por passagem de status.
Fila e baixa qualidade: uma linha por projeto. ambiente_origem e a origem da
passagem, nao a localizacao atual do cadastro. Cadastro atual nao prova equipe
responsavel historica. Nao somar projetos distintos de grupos como se exclusivos.

## 1. Distribuicao por ambiente, corte e estimativas

Explica quem compoe o SLA publicado. Somente ViU2 pode refletir a regra de
qualidade da migracao; nao usar esse resultado como retrato de toda a operacao.

```sql
SELECT ambiente_origem, versao_contrato, corte_globocorp_utc,
  COUNT(*) AS passagens, COUNT(DISTINCT projeto_id) AS projetos,
  COUNT(sla_etapa_horas_uteis) AS passagens_observadas,
  COUNTIF(origem_duracao_analise = 'estimada') AS passagens_estimadas,
  MAX(cadastro_atual_capturado_em) AS ultima_captura_cadastro
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY 1, 2, 3 ORDER BY 1, 3 DESC;
```

## 2. Reconciliacao dos destinos e chaves

Exigir zero IDs nulos/duplicados na consulta abaixo. Total distinto e soma
devem coincidir; isso nao comprova cobertura de todos os itens do board.

```sql
WITH destinos AS (
  SELECT DISTINCT 'sla' AS destino, projeto_id
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  UNION ALL
  SELECT 'fila', projeto_id
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_fila_precificacao`
  UNION ALL
  SELECT 'qualidade', projeto_id
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_baixa_qualidade_de_dado`
)
SELECT COUNT(*) AS projetos_somados, COUNT(DISTINCT projeto_id) AS projetos_distintos,
  COUNT(*) - COUNT(DISTINCT projeto_id) AS repeticoes_ou_nulos,
  COUNTIF(projeto_id IS NULL) AS ids_nulos
FROM destinos;
```

```sql
SELECT COUNT(*) AS passagens,
  COUNT(*) - COUNT(DISTINCT interval_id) AS chaves_repetidas_ou_nulas,
  COUNTIF(sla_etapa_horas_uteis IS DISTINCT FROM
    IF(elegivel_comparacao, duracao_horas_uteis, NULL)) AS divergencias_kpi,
  COUNTIF(entrega_precificacao_observada AND (
    inicio_precificacao_utc IS NULL OR fim_precificacao_utc IS NULL
    OR fim_precificacao_utc < inicio_precificacao_utc
    OR precificacao_horas_corridas IS NULL OR precificacao_horas_uteis IS NULL
    OR precificacao_horas_corridas < 0 OR precificacao_horas_uteis < 0
    OR precificacao_horas_uteis > precificacao_horas_corridas + 0.001
  )) AS entregas_invalidas
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`;
```

## 3. Motivos de baixa qualidade — por que saiu do SLA?

Motivos podem coexistir: nao somar projetos entre motivos.

```sql
SELECT motivo, COUNT(DISTINCT projeto_id) AS projetos
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_baixa_qualidade_de_dado`,
UNNEST(JSON_VALUE_ARRAY(motivos_json)) AS motivo
GROUP BY motivo ORDER BY projetos DESC;
```

## 4. Exemplos vinculados entre ambientes para revisar amanha

Nao aprova automaticamente continuidade. Escolhe dez projetos e mostra TODAS
as passagens preservadas no registro de qualidade, para nao truncar a cronologia.

```sql
WITH exemplos AS (
  SELECT *
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_baixa_qualidade_de_dado`
  WHERE 'continuidade_entre_ambientes_nao_homologada'
    IN UNNEST(JSON_VALUE_ARRAY(motivos_json))
  ORDER BY projeto_id LIMIT 10
)
SELECT q.projeto_id, q.projeto_nome, q.marca, q.talento,
  q.item_id_viu2, q.item_id_globocorp, q.motivos_json,
  JSON_VALUE(e, '$.ambiente_origem') AS ambiente,
  SAFE_CAST(JSON_VALUE(e, '$.ordem_etapa') AS INT64) AS ordem,
  JSON_VALUE(e, '$.status_nome') AS status,
  JSON_VALUE(e, '$.entrada_status_utc') AS entrada_utc,
  JSON_VALUE(e, '$.saida_status_utc') AS saida_observada_utc
FROM exemplos q, UNNEST(JSON_QUERY_ARRAY(q.evidencias_passagens_json)) AS e
ORDER BY q.projeto_id, ordem;
```

## 5. Tempo de entrega de precificacao — ciclos observados

Entrada ate entrega em Aguardando Feedback, conforme contrato de precificacao.
Horas corridas elegiveis e horas uteis elegiveis descontam pausas previstas na
regra; janela e o tempo total transcorrido. Nao chamar estimativa de observado.
Agrupar por mes da entrega permite acompanhar mudanca, mas comparar tambem
mix de projetos e cobertura. P50=mediana; P90=90% dos ciclos ate esse prazo.
Nao e meta contratada nem tempo por pessoa. Reaberturas podem gerar varios ciclos.

```sql
SELECT DATE_TRUNC(DATE(fim_precificacao_utc, 'America/Sao_Paulo'), MONTH) AS mes,
  COUNT(*) AS entregas, COUNT(DISTINCT ciclo_precificacao_id) AS ciclos,
  COUNT(DISTINCT projeto_id) AS projetos,
  ROUND(AVG(janela_precificacao_horas_corridas), 2) AS media_janela_corrida,
  ROUND(AVG(pausas_precificacao_horas_corridas), 2) AS media_pausas_corridas,
  ROUND(AVG(precificacao_horas_corridas), 2) AS media_horas_corridas_elegiveis,
  ROUND(AVG(precificacao_horas_uteis), 2) AS media_horas_uteis,
  APPROX_QUANTILES(precificacao_horas_uteis, 100)[OFFSET(50)] AS p50_horas_uteis,
  APPROX_QUANTILES(precificacao_horas_uteis, 100)[OFFSET(90)] AS p90_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE entrega_precificacao_observada IS TRUE
GROUP BY mes ORDER BY mes;
```

## 6. Permanencia por status — localizar candidatos a gargalo

Analise descritiva por passagem observada, nao participacao no ciclo de
precificacao. Pode incluir etapas fora desse ciclo; antes de apresentar como
gargalo de precificacao, restringir aos papeis e ciclos definidos no contrato.
Permanencia nao comprova trabalho ativo nem produtividade individual.

```sql
SELECT status_nome, COUNT(*) AS passagens_observadas,
  COUNT(DISTINCT projeto_id) AS projetos,
  ROUND(SUM(sla_etapa_horas_uteis), 2) AS horas_uteis_acumuladas,
  ROUND(AVG(sla_etapa_horas_uteis), 2) AS media_horas_uteis,
  APPROX_QUANTILES(sla_etapa_horas_uteis, 100)[OFFSET(50)] AS p50_horas_uteis,
  APPROX_QUANTILES(sla_etapa_horas_uteis, 100)[OFFSET(90)] AS p90_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE sla_etapa_horas_uteis IS NOT NULL
GROUP BY status_nome ORDER BY horas_uteis_acumuladas DESC;
```

## 7. Fila — projetos ainda somente em Entrada

Idade calculada ate a captura, nao ate NOW(). Escopo da populacao consolidada,
nao todo o backlog Monday. Mostra prioridades de triagem, nao atrasos sem meta.

```sql
SELECT projeto_id, projeto_nome, marca, talento, entrada_fila_utc,
  espera_ate_utc, espera_horas_corridas, espera_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_fila_precificacao`
ORDER BY espera_horas_uteis DESC;
```

## Aceite

Zero erros estruturais e reconciliacao sao necessarios, mas nao suficientes:
validar amostras com historico original, calendario/feriados e evidencia de
continuidade. Nao usar a base filtrada como KPI de toda a operacao sem declarar
quem ficou fora. Proxima pauta: docs/RETOMADA_2026_09_25.md.
