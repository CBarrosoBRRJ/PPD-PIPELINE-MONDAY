-- Consumo apenas apos publicacao conferida do contrato v3. Sem escrita.
-- Populacao selecionada da consolidada, nao toda a operacao.
-- Retornos contam como passagens distintas; nao somar ambientes como ciclo global.
-- Se usar periodo, filtrar por saida_status_utc explicitamente.
SELECT
  ambiente_origem,
  status_nome,
  COUNT(*) AS passagens_no_recorte,
  COUNTIF(elegivel_comparacao AND validacao_negocio = 'aprovado_etapa_origem_v1') AS passagens_kpi,
  COUNT(DISTINCT IF(elegivel_comparacao AND validacao_negocio = 'aprovado_etapa_origem_v1', item_id, NULL)) AS projetos_kpi,
  AVG(IF(elegivel_comparacao AND validacao_negocio = 'aprovado_etapa_origem_v1', duracao_horas_uteis, NULL)) AS media_horas_uteis,
  MIN(corte_globocorp_utc) AS corte_minimo,
  MAX(corte_globocorp_utc) AS corte_maximo
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE versao_contrato IN ('sla-consolidado-etapa-v3', 'sla-consolidado-consumo-v4')
GROUP BY ambiente_origem, status_nome
ORDER BY ambiente_origem, status_nome;
