-- Candidato v8: executar apenas após implantação e reconciliação desse contrato.
-- Não usar este SQL na produção v7: os campos novos ainda não existem lá.
-- Uma linha por entrega aprovada, nunca média dos totais repetidos por etapa.
SELECT
  ambiente_origem,
  COUNT(*) AS entregas_observadas,
  COUNT(DISTINCT projeto_id) AS projetos,
  AVG(precificacao_horas_corridas) AS media_horas_corridas,
  AVG(precificacao_horas_uteis) AS media_horas_uteis,
  APPROX_QUANTILES(precificacao_horas_uteis, 100)[SAFE_OFFSET(50)] AS p50_horas_uteis,
  APPROX_QUANTILES(precificacao_horas_uteis, 100)[SAFE_OFFSET(90)] AS p90_horas_uteis,
  AVG(pausas_precificacao_horas_corridas) AS media_pausas_corridas
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE versao_contrato = 'sla-consolidado-precificacao-v8'
  AND entrega_precificacao_observada
GROUP BY ambiente_origem;
