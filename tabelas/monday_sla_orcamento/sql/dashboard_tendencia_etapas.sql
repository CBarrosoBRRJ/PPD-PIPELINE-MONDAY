-- BigQuery Standard SQL, somente leitura. Conferência para a página de etapas.
-- Semana da saída observada na hora local; não é tendência do lead time global.
-- Percentis aproximados; a medida DAX PERCENTILEX.INC pode diferir ligeiramente.
SELECT
  DATE_TRUNC(DATE(saida_status_local), WEEK(MONDAY)) AS semana_saida_local,
  ambiente_origem,
  status_nome,
  COUNT(*) AS passagens_observadas,
  COUNT(DISTINCT projeto_id) AS projetos_observados,
  ROUND(AVG(sla_etapa_horas_uteis), 3) AS media_horas_uteis,
  ROUND(APPROX_QUANTILES(sla_etapa_horas_uteis, 100)[OFFSET(50)], 3)
    AS p50_aproximado_horas_uteis,
  ROUND(APPROX_QUANTILES(sla_etapa_horas_uteis, 100)[OFFSET(90)], 3)
    AS p90_aproximado_horas_uteis,
  ROUND(SUM(sla_etapa_horas_uteis), 3) AS exposicao_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE sla_etapa_horas_uteis IS NOT NULL
  AND saida_status_local IS NOT NULL
GROUP BY 1, 2, 3
ORDER BY 1 DESC, 2, 3;
