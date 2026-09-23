-- Somente apos publicacao v4. Media por passagem encerrada elegivel, por origem.
-- NULL fora do KPI; zero observado conta no denominador. Nao usar COALESCE(...,0).
SELECT ambiente_origem, status_nome,
  COUNT(*) AS passagens_total,
  COUNT(sla_etapa_horas_uteis) AS passagens_kpi,
  COUNT(DISTINCT IF(sla_etapa_horas_uteis IS NOT NULL, item_id, NULL)) AS projetos_kpi,
  ROUND(AVG(sla_etapa_horas_uteis), 3) AS media_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY ambiente_origem, status_nome
ORDER BY ambiente_origem, status_nome;
