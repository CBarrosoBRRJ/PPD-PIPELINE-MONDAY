-- Somente leitura apos publicar v15/v9. Cada contador de violacao deve ser zero.
WITH base AS (
  SELECT *, ARRAY(
    SELECT TRIM(nome)
    FROM UNNEST(IFNULL(JSON_VALUE_ARRAY(cadastro_atual_talentos_exclusivos_json), ARRAY<STRING>[])) nome
    WHERE NULLIF(TRIM(nome), '') IS NOT NULL
  ) AS exclusivos,
  NULLIF(TRIM(cadastro_atual_interveniencia), '') AS interveniencia
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
)
SELECT versao_contrato,
  COUNT(*) AS passagens,
  COUNT(DISTINCT projeto_id) AS projetos,
  COUNT(*) - COUNT(DISTINCT interval_id) AS chaves_repetidas_ou_nulas,
  COUNTIF(ARRAY_LENGTH(exclusivos) > 0 AND interveniencia IS NOT NULL) AS ambas_colunas,
  COUNTIF(ARRAY_LENGTH(exclusivos) = 0 AND interveniencia IS NULL) AS nenhum_talento,
  COUNTIF(ARRAY_LENGTH(exclusivos) > 1) AS multiplos_exclusivos,
  COUNTIF(REGEXP_CONTAINS(
    NORMALIZE_AND_CASEFOLD(CONCAT(ARRAY_TO_STRING(exclusivos, ' '), ' ', COALESCE(interveniencia, '')), NFKC),
    r'\bsquad\b')) AS com_squad,
  COUNTIF(cadastro_atual_capturado_em IS NULL) AS sem_cadastro,
  COUNTIF(eh_interveniencia IS NOT NULL AND
    eh_interveniencia IS DISTINCT FROM (interveniencia IS NOT NULL)) AS indicador_divergente
FROM base
GROUP BY versao_contrato;
