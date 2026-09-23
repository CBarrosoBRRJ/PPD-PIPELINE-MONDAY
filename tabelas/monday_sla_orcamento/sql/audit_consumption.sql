-- Somente leitura. Zero anomalias nao aprova identidade, Input ou KPI automaticamente.
-- Nao recalcula calendario nem soma ciclos entre contas.
SELECT
  COUNT(*) AS passagens,
  COUNT(DISTINCT projeto_id) AS projetos,
  COUNT(*) - COUNT(DISTINCT interval_id) AS chaves_duplicadas,
  MIN(corte_globocorp_utc) AS corte_minimo,
  MAX(corte_globocorp_utc) AS corte_maximo,
  COUNTIF(entrada_status_utc IS NULL OR ordem_etapa IS NULL) AS sem_cronologia,
  COUNTIF(saida_status_utc < entrada_status_utc) AS saida_antes_entrada,
  COUNTIF(duracao_horas < 0 OR duracao_horas_uteis < 0) AS duracoes_negativas,
  COUNTIF(duracao_horas_uteis > duracao_horas + 0.001) AS uteis_excedem_corridas,
  COUNTIF(duracao_horas IS NOT NULL AND (
    entrada_status_utc IS NULL OR saida_status_utc IS NULL
    OR ABS(duracao_horas - TIMESTAMP_DIFF(saida_status_utc, entrada_status_utc, MICROSECOND)
      / 3600000000.0) > 0.002
  )) AS duracao_sem_limites_coerentes,
  COUNTIF(status_terminal IS TRUE AND (
    duracao_horas IS NOT NULL OR duracao_horas_uteis IS NOT NULL
    OR finalizacao_observada_utc IS DISTINCT FROM entrada_status_utc
  )) AS terminal_invalido,
  COUNTIF(saida_status_utc IS NULL AND status_terminal IS FALSE) AS sem_saida_nao_terminal,
  COUNTIF(elegivel_comparacao) AS elegiveis_comparacao,
  COUNTIF(continuidade_validada) AS continuidade_validada,
  COUNTIF(validacao_negocio = 'pendente') AS validacao_pendente
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`;

SELECT ambiente_origem, situacao_sla_registro, validacao_negocio,
  COUNT(*) AS passagens, COUNT(DISTINCT projeto_id) AS projetos,
  COUNTIF(duracao_horas IS NOT NULL) AS com_duracao
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY ambiente_origem, situacao_sla_registro, validacao_negocio
ORDER BY ambiente_origem, situacao_sla_registro;
