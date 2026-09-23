-- Somente leitura. Executar no editor BigQuery/DBeaver, não diretamente no Bash.
-- Resultado é diagnóstico: ciclo observado na origem != entrega global homologada.
-- tempo_ciclo_observado_horas é CORRIDO; não converter em útil dividindo por jornada.
SELECT
  ambiente_origem,
  COUNT(*) AS passagens,
  COUNTIF(tempo_ciclo_observado_horas IS NOT NULL) AS registros_com_ciclo_origem,
  COUNT(DISTINCT IF(tempo_ciclo_observado_horas IS NOT NULL, projeto_id, NULL))
    AS projetos_com_ciclo_origem,
  MIN(tempo_ciclo_observado_horas) AS menor_ciclo_origem_h_corridas,
  MAX(tempo_ciclo_observado_horas) AS maior_ciclo_origem_h_corridas
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY ambiente_origem;

-- Inspecionar marco inicial, final, motivo de encerramento e reabertura antes
-- de construir fato de ciclos. Não somar este total com durações das passagens.
SELECT
  projeto_id, ambiente_origem, item_id, ordem_etapa, status_nome,
  entrada_status_utc, saida_status_utc, ciclo_observado_origem,
  reabertura_comprovada_origem, tempo_ciclo_observado_horas,
  continuidade_validada, qualidade_trajetoria, limitacoes_trajetoria_json
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE tempo_ciclo_observado_horas IS NOT NULL
ORDER BY ambiente_origem, projeto_id, ordem_etapa
LIMIT 100;
