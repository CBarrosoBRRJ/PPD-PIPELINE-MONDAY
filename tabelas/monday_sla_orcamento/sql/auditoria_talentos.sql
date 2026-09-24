-- Somente leitura, APOS publicacao do contrato v9.
SELECT
  versao_contrato, situacao_talento_atual, eh_interveniencia,
  COUNT(*) AS passagens,
  COUNT(DISTINCT projeto_id) AS projetos,
  COUNTIF(
    (situacao_talento_atual = 'rotulo_unico_na_origem'
      AND (talento_nome_atual IS NULL OR eh_interveniencia IS NULL))
    OR (situacao_talento_atual != 'rotulo_unico_na_origem'
      AND (talento_nome_atual IS NOT NULL OR eh_interveniencia IS NOT NULL))
  ) AS escalares_inconsistentes,
  COUNT(sla_etapa_horas_uteis) AS passagens_kpi_observado
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY 1, 2, 3
ORDER BY 2, 3;
