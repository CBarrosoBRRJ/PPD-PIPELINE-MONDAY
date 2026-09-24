-- Somente leitura. Comparar capturas antes de interpretar divergencias:
-- uma nova publicacao do backlog pode preceder a atualizacao da consolidada.
WITH comparado AS (
  SELECT s.*,
    b.item_id AS item_cadastro,
    b.capturado_em AS captura_backlog,
    TO_JSON_STRING(STRUCT(
      s.cadastro_atual_marca AS marca,
      s.cadastro_atual_talentos_exclusivos_json AS talentos,
      s.cadastro_atual_interveniencia AS interveniencia,
      s.cadastro_atual_orcamento_json AS orcamento,
      s.cadastro_atual_talent_manager_json AS talent_manager,
      s.cadastro_atual_gp_json AS gp,
      s.cadastro_atual_conteudo_json AS conteudo,
      s.cadastro_atual_producao_json AS producao,
      s.cadastro_atual_audiencia_json AS audiencia,
      s.cadastro_atual_tipo_projeto AS tipo_projeto,
      s.cadastro_atual_tipo_input AS tipo_input,
      s.cadastro_atual_tipo_output AS tipo_output
    )) IS DISTINCT FROM TO_JSON_STRING(STRUCT(
      b.marca AS marca, b.talentos_exclusivos_json AS talentos,
      b.interveniencia AS interveniencia, b.orcamento_json AS orcamento,
      b.talent_manager_json AS talent_manager, b.gp_json AS gp,
      b.conteudo_json AS conteudo, b.producao_json AS producao,
      b.audiencia_json AS audiencia, b.tipo_projeto AS tipo_projeto,
      b.tipo_input AS tipo_input, b.tipo_output AS tipo_output
    )) AS atributos_divergentes
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento` s
  LEFT JOIN `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_backlog_agenciamento_2026` b
    ON s.item_id_globocorp = b.item_id
    AND b.board_id = 18429499488
)
SELECT versao_contrato,
  COUNT(*) AS passagens_apos_join,
  COUNT(DISTINCT interval_id) AS intervalos_distintos,
  COUNTIF(interval_id IS NULL) AS intervalos_sem_chave,
  COUNTIF(item_cadastro IS NULL) AS sem_correspondencia,
  COUNTIF(cadastro_atual_capturado_em IS NULL) AS sem_captura,
  COUNTIF(cadastro_atual_capturado_em IS DISTINCT FROM captura_backlog) AS capturas_divergentes,
  COUNTIF(atributos_divergentes) AS divergencias_nos_12_atributos
FROM comparado
GROUP BY versao_contrato;
