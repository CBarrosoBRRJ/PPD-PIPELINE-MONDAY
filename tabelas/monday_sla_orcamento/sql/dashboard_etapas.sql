-- Somente leitura; executar no editor SQL do BigQuery/DBeaver.
-- KPI observado por ambiente e status. Percentis aproximados, não metas de SLA.
-- Para período de conclusão, filtrar saida_status_local nas linhas elegíveis.
-- Não usar este filtro de período no drill-through da trajetória completa.
SELECT
  ambiente_origem,
  status_nome,
  COUNT(*) AS passagens_total,
  COUNT(sla_etapa_horas_uteis) AS passagens_kpi,
  COUNT(DISTINCT IF(sla_etapa_horas_uteis IS NOT NULL, projeto_id, NULL)) AS projetos_kpi,
  AVG(sla_etapa_horas_uteis) AS media_observada_horas_uteis,
  APPROX_QUANTILES(sla_etapa_horas_uteis, 100)[SAFE_OFFSET(50)] AS mediana_aproximada,
  APPROX_QUANTILES(sla_etapa_horas_uteis, 100)[SAFE_OFFSET(75)] AS p75_aproximado,
  APPROX_QUANTILES(sla_etapa_horas_uteis, 100)[SAFE_OFFSET(90)] AS p90_aproximado,
  COUNT(duracao_analise_horas_uteis) AS passagens_analise,
  COUNTIF(origem_duracao_analise = 'estimada') AS passagens_estimadas,
  SAFE_DIVIDE(COUNTIF(origem_duracao_analise = 'estimada'),
              COUNT(duracao_analise_horas_uteis)) AS fracao_estimada_na_analise,
  AVG(duracao_analise_horas_uteis) AS media_analise_com_hipoteses,
  MIN(corte_globocorp_utc) AS corte_minimo,
  MAX(corte_globocorp_utc) AS corte_maximo
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY ambiente_origem, status_nome
ORDER BY ambiente_origem, status_nome;
