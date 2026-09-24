-- BigQuery Standard SQL; somente leitura. Executar cada SELECT separadamente
-- no editor BigQuery ou em bq query. Não executar SQL diretamente no Bash.
-- Confere população e proveniência do corte atual sem misturar estimativa com KPI.
SELECT
  corte_globocorp_utc,
  versao_contrato,
  ambiente_origem,
  origem_duracao_analise,
  COUNT(*) AS passagens,
  COUNT(DISTINCT projeto_id) AS projetos,
  COUNT(sla_etapa_horas_uteis) AS kpi_etapa_observado,
  COUNT(duracao_analise_horas_uteis) AS duracoes_para_analise,
  COUNTIF(origem_duracao_analise = 'estimada'
          AND sla_etapa_horas_uteis IS NOT NULL) AS estimativas_no_kpi
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY 1, 2, 3, 4
ORDER BY 1 DESC, 3, 4;

-- Integridade básica do novo corte. Zero nos campos *_invalidas é esperado.
SELECT
  COUNT(*) AS passagens,
  COUNT(DISTINCT projeto_id) AS projetos,
  COUNT(*) - COUNT(DISTINCT interval_id) AS chaves_duplicadas,
  COUNTIF(entrada_status_utc IS NULL OR ordem_etapa IS NULL) AS cronologia_invalida,
  COUNTIF(saida_status_utc < entrada_status_utc) AS saida_invalida,
  COUNTIF(duracao_analise_horas < 0 OR duracao_analise_horas_uteis < 0)
    AS duracoes_invalidas,
  COUNTIF(duracao_analise_horas_uteis > duracao_analise_horas + 0.001)
    AS horas_uteis_invalidas,
  COUNTIF(origem_duracao_analise = 'estimada'
          AND sla_etapa_horas_uteis IS NOT NULL) AS estimativas_no_kpi
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`;
