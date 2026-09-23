-- DBeaver/BigQuery SQL editor, only after contract v6 is published.
-- Supply @projeto_id. Keep estimates visibly separate from official metrics.
SELECT projeto_id, ordem_etapa, ambiente_origem, item_id, projeto_nome, status_nome,
       entrada_status_local, saida_status_local AS saida_observada_local,
       saida_estimada_local, metodo_estimativa,
       sla_etapa_horas_uteis AS kpi_oficial_etapa_horas_uteis,
       duracao_estimada_horas_uteis AS hipotese_etapa_horas_uteis,
       interval_id_referencia_estimativa, qualidade_trajetoria,
       limitacoes_trajetoria_json
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE projeto_id = @projeto_id
ORDER BY projeto_id, ordem_etapa;
