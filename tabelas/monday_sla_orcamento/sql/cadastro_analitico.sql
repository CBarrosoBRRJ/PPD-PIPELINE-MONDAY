-- Consulta somente leitura para DBeaver/BigQuery; requer contrato v9 (candidato).
-- Uma linha por passagem: nao expandir arrays de pessoas/talentos antes de somar SLA.
-- Cadastro atual NAO comprova quem era responsavel na data de uma passagem antiga.
-- Classificacao abaixo descreve preenchimento das colunas, nao vinculo contratual.
WITH base AS (
  SELECT *,
    EXISTS (
      SELECT 1
      FROM UNNEST(IFNULL(JSON_VALUE_ARRAY(cadastro_atual_talentos_exclusivos_json), ARRAY<STRING>[])) AS nome
      WHERE NULLIF(TRIM(nome), '') IS NOT NULL
    ) AS tem_exclusivos,
    NULLIF(TRIM(cadastro_atual_interveniencia), '') IS NOT NULL AS tem_interveniencia
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
)
SELECT
  projeto_id, interval_id, item_id_globocorp, ambiente_origem,
  projeto_nome, ordem_etapa, status_nome,
  cadastro_atual_marca AS marca_atual,
  cadastro_atual_talentos_exclusivos_json AS talentos_exclusivos_atuais_json,
  cadastro_atual_interveniencia AS interveniencia_atual,
  talento_nome_atual,
  eh_interveniencia,
  talentos_atuais_json,
  situacao_talento_atual,
  CASE
    WHEN tem_exclusivos AND tem_interveniencia THEN 'ambos'
    WHEN tem_exclusivos THEN 'exclusivos'
    WHEN tem_interveniencia THEN 'interveniencia'
    ELSE 'nao_informado'
  END AS origem_talentos_cadastro_atual,
  cadastro_atual_orcamento_json AS responsaveis_orcamento_atuais_json,
  cadastro_atual_talent_manager_json AS talent_managers_atuais_json,
  cadastro_atual_gp_json AS responsaveis_gp_atuais_json,
  cadastro_atual_conteudo_json AS responsaveis_conteudo_atuais_json,
  cadastro_atual_producao_json AS responsaveis_producao_atuais_json,
  cadastro_atual_audiencia_json AS responsaveis_audiencia_atuais_json,
  cadastro_atual_tipo_projeto AS tipo_projeto_atual,
  cadastro_atual_tipo_input AS tipo_input_atual,
  cadastro_atual_tipo_output AS tipo_output_atual,
  cadastro_atual_capturado_em,
  entrada_status_local, saida_status_local, saida_estimada_local,
  duracao_analise_horas, duracao_analise_horas_uteis, origem_duracao_analise,
  sla_etapa_horas_uteis,
  entrega_precificacao_observada, situacao_ciclo_precificacao,
  precificacao_horas_corridas, precificacao_horas_uteis,
  versao_contrato
FROM base
ORDER BY projeto_id, ordem_etapa
LIMIT 100;
