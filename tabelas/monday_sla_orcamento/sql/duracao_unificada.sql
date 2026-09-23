-- DBeaver/BigQuery editor; after contract sla-consolidado-analise-v7 publication.
SELECT projeto_id, ordem_etapa, ambiente_origem, status_nome, entrada_status_local,
       COALESCE(saida_status_local, saida_estimada_local) AS saida_para_visualizacao,
       saida_status_local IS NULL AND saida_estimada_local IS NOT NULL AS saida_e_estimada,
       duracao_analise_horas, duracao_analise_horas_uteis, origem_duracao_analise,
       sla_etapa_horas_uteis AS kpi_estritamente_observado
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE projeto_id = @projeto_id
ORDER BY projeto_id, ordem_etapa;

-- Analytical indicator including hypotheses: always display the estimate share.
SELECT ambiente_origem, status_nome,
       COUNT(duracao_analise_horas_uteis) AS passagens_com_duracao,
       COUNTIF(origem_duracao_analise = 'estimada') AS passagens_estimadas,
       ROUND(AVG(duracao_analise_horas), 3) AS media_horas_corridas,
       ROUND(AVG(duracao_analise_horas_uteis), 3) AS media_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY ambiente_origem, status_nome
ORDER BY ambiente_origem, status_nome;
