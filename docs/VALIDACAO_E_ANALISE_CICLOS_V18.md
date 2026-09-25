# Consultas de ciclos v18

Executar somente DEPOIS da publicacao v18. Os blocos SQL sao para o editor do
BigQuery, nao diretamente no Bash. Para Cloud Shell: bq --project_id=gglobo-viu-dados-hdg-prd
query --location=US --use_legacy_sql=false --use_cache=false
--maximum_bytes_billed=1073741824 'SQL AQUI'. Consultas podem consumir cota/custo.

## 1. Integridade: todas as colunas de problemas devem ser zero

```sql
WITH s AS (
  SELECT * FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
), c AS (
  SELECT * FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
)
SELECT
  (SELECT COUNT(*) - COUNT(DISTINCT interval_id) FROM s) AS problemas_chave_passagem,
  (SELECT COUNT(*) - COUNT(DISTINCT ciclo_id) FROM c) AS problemas_chave_ciclo,
  (SELECT COUNT(*) FROM s WHERE ciclo_id IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM c WHERE c.ciclo_id=s.ciclo_id AND c.projeto_id=s.projeto_id
  )) AS passagens_orfas,
  (SELECT COUNT(*) FROM c WHERE NOT EXISTS (
    SELECT 1 FROM s WHERE s.interval_id=c.interval_id_inicio
    AND s.ciclo_id=c.ciclo_id AND s.projeto_id=c.projeto_id
  )) AS inicios_orfaos,
  (SELECT COUNT(*) FROM c WHERE interval_id_fim IS NOT NULL AND NOT EXISTS (
    SELECT 1 FROM s WHERE s.interval_id=c.interval_id_fim
    AND s.ciclo_id=c.ciclo_id AND s.projeto_id=c.projeto_id
  )) AS fins_orfaos,
  (SELECT COUNT(*) FROM c WHERE fim_utc < inicio_utc OR inicio_utc > corte_utc
    OR fim_utc > corte_utc OR (situacao='em_andamento') != (fim_utc IS NULL)
    OR operacao_horas_corridas < 0 OR operacao_horas_uteis < 0
    OR operacao_horas_uteis > operacao_horas_corridas + 0.001
    OR (kpi_entrega_observada AND (NOT duracao_completa OR contem_estimativa
       OR contem_idade_aberta OR situacao!='entregue'))
  ) AS ciclos_inconsistentes,
  (SELECT COUNT(*) FROM s WHERE sla_versao_regra IS NULL OR sla_categoria_tempo IS NULL
    OR sla_origem_duracao IS NULL OR sla_horas_corridas < 0 OR sla_horas_uteis < 0
    OR sla_horas_uteis > sla_horas_corridas + 0.001
  ) AS passagens_inconsistentes,
  (SELECT COUNT(*) FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_fila_precificacao` f
    WHERE NOT EXISTS (SELECT 1 FROM s WHERE s.projeto_id=f.projeto_id)
  ) AS fila_fora_da_principal;
```

## 2. Populacao e cobertura (sem somar fatos)

Reconcilie tambem os totais dos ciclos com as passagens operacionais; resultado
esperado zero. Isso e independente das contagens do log de publicacao.

```sql
WITH p AS (
  SELECT ciclo_id, COUNT(*) AS passagens, COUNT(sla_horas_corridas) AS medidas,
    SUM(sla_horas_corridas) AS corridas, SUM(sla_horas_uteis) AS uteis
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  WHERE sla_categoria_tempo='operacao' AND ciclo_id IS NOT NULL
  GROUP BY ciclo_id
)
SELECT COUNT(*) AS ciclos_com_total_divergente
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento` c
LEFT JOIN p USING(ciclo_id)
WHERE p.ciclo_id IS NULL OR p.passagens != c.quantidade_passagens_operacionais
  OR (c.duracao_completa AND (p.passagens != p.medidas
    OR c.operacao_horas_corridas IS NULL OR c.operacao_horas_uteis IS NULL
    OR ABS(p.corridas-c.operacao_horas_corridas)>0.002
    OR ABS(p.uteis-c.operacao_horas_uteis)>0.002));
```

```sql
SELECT ambiente_origem, sla_categoria_tempo, sla_origem_duracao,
  COUNT(*) AS passagens, COUNT(DISTINCT projeto_id) AS projetos,
  COUNT(DISTINCT sla_grupo_permanencia_id) AS permanencias,
  COUNT(sla_horas_uteis) AS passagens_com_tempo
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY 1,2,3 ORDER BY 1,2,3;

SELECT situacao, contem_estimativa, contem_idade_aberta, duracao_completa,
  COUNT(*) AS ciclos, COUNT(DISTINCT projeto_id) AS projetos,
  COUNTIF(kpi_entrega_observada) AS entregas_kpi_observado
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
GROUP BY 1,2,3,4 ORDER BY 1,2,3,4;
```

Contagens de projetos por categoria/origem/ciclo se sobrepoem. A reconciliacao
total fonte/aceitos/excluidos esta no report privado referenciado pela publicacao.

## 3. KPI observado por tipo de ciclo

```sql
SELECT tipo_ciclo, COUNT(*) AS entregas,
  AVG(operacao_horas_uteis) AS media_horas_uteis,
  APPROX_QUANTILES(operacao_horas_uteis,100)[OFFSET(50)] AS mediana_horas_uteis,
  APPROX_QUANTILES(operacao_horas_uteis,100)[OFFSET(90)] AS p90_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
WHERE kpi_entrega_observada
GROUP BY tipo_ciclo;
```

Sem meta acordada, P90 nao significa atraso. Horas sao permanencia operacional,
nao horas de esforco individual. Estimativas devem ter painel/filtro explicito.

## 4. Andamento e espera externa

```sql
SELECT projeto_id, numero_ciclo, inicio_utc, operacao_horas_uteis,
  contem_estimativa, contem_idade_aberta, duracao_completa, motivos_json
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
WHERE situacao='em_andamento'
ORDER BY inicio_utc;

SELECT sla_categoria_tempo, sla_origem_duracao,
  COUNT(*) AS passagens, COUNT(sla_horas_uteis) AS tempos_disponiveis,
  SUM(sla_horas_uteis) AS soma_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE sla_categoria_tempo IN ('feedback','terceiros','standby')
GROUP BY 1,2;
```

Nao converter nulos em zero. Ciclos abertos sem duracao completa continuam
visiveis para acompanhamento, mas nao entram em media de entregas.

## 5. Ciclos por marca/talento sem multiplicar as medidas

```sql
WITH projeto AS (
  SELECT projeto_id, cadastro_atual_marca AS marca, talento_nome_atual AS talento,
    eh_interveniencia, cadastro_atual_tipo_projeto AS tipo_projeto
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  QUALIFY ROW_NUMBER() OVER(PARTITION BY projeto_id ORDER BY ordem_etapa,interval_id)=1
)
SELECT p.marca, p.talento, p.eh_interveniencia, p.tipo_projeto,
  COUNT(*) AS entregas_observadas, AVG(c.operacao_horas_uteis) AS media_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento` c
JOIN projeto p USING(projeto_id)
WHERE c.kpi_entrega_observada
GROUP BY 1,2,3,4;
```

## 6. Amostras entre ambientes e retornos

```sql
WITH exemplos AS (
  SELECT projeto_id
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  GROUP BY projeto_id HAVING COUNT(DISTINCT ambiente_origem)=2
  ORDER BY projeto_id LIMIT 5
)
SELECT s.projeto_id, s.projeto_nome, s.ambiente_origem, s.status_nome,
  s.entrada_status_utc, s.saida_status_utc, s.sla_saida_estimada_utc,
  s.ciclo_id, s.sla_origem_duracao, s.sla_horas_uteis, s.sla_motivos_json
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento` s
JOIN exemplos USING(projeto_id)
ORDER BY projeto_id, entrada_status_utc;

SELECT projeto_id, COUNT(*) AS ciclos, COUNTIF(situacao='entregue') AS entregas
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
GROUP BY projeto_id HAVING COUNT(*)>1 ORDER BY ciclos DESC LIMIT 20;
```

Estimativa na fronteira e hipotese, nao prova de historico completo. Conferir
o inicio Entrada, a passagem que encerra cada ciclo e as revisoes posteriores.
Na qualidade, motivos sao listas sobrepostas: nao somar contagens por motivo.
