-- Run only after contract sla-consolidado-trajetoria-v5 is published.
-- One final observed row per project avoids double counting repeated project fields.
SELECT qualidade_trajetoria,
       COUNT(*) AS projetos,
       COUNTIF(quantidade_passagens_projeto = 1) AS projetos_passagem_unica
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE eh_ultima_etapa_observada
GROUP BY qualidade_trajetoria
ORDER BY qualidade_trajetoria;
