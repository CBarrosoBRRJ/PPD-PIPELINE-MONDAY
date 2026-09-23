-- BigQuery SQL editor. Supply the unified project ID, NOT a native item ID.
-- Ordered observations do not prove uninterrupted history or total SLA.
SELECT
  projeto_id, ordem_etapa, ambiente_origem, item_id,
  item_id_viu2, item_id_globocorp, projeto_nome, status_nome,
  entrada_status_local, saida_status_local,
  classificacao_consumo, sla_etapa_horas_uteis,
  motivos_inelegibilidade_kpi_json,
  quantidade_passagens_projeto, qualidade_trajetoria,
  limitacoes_trajetoria_json, eh_ultima_etapa_observada
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE projeto_id = @projeto_id
ORDER BY projeto_id, ordem_etapa;
