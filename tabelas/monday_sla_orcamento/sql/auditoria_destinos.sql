-- Somente leitura, APOS primeira publicacao v17 confirmada.
-- Totais de referencia sao dinamicos, nao constantes de validacao.
WITH projetos AS (
  SELECT DISTINCT projeto_id, 'sla' AS destino
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  UNION ALL
  SELECT projeto_id, 'fila'
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_fila_precificacao`
  UNION ALL
  SELECT projeto_id, 'qualidade'
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_baixa_qualidade_de_dado`
)
SELECT COUNT(*) AS projetos_somados,
  COUNT(DISTINCT projeto_id) AS projetos_distintos,
  COUNT(*) - COUNT(DISTINCT projeto_id) AS duplicidades_entre_destinos_ou_resumos
FROM projetos;

SELECT 'sla' AS destino, COUNT(*) AS linhas,
  COUNT(DISTINCT projeto_id) AS projetos, COUNT(*) AS passagens_representadas
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
UNION ALL
SELECT 'fila', COUNT(*), COUNT(DISTINCT projeto_id), COALESCE(SUM(quantidade_passagens), 0)
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_fila_precificacao`
UNION ALL
SELECT 'qualidade', COUNT(*), COUNT(DISTINCT projeto_id), COALESCE(SUM(quantidade_passagens), 0)
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_baixa_qualidade_de_dado`;
