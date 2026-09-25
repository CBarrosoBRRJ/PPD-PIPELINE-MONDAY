-- Referencia; criacao controlada pelo journal de destinos.
CREATE TABLE `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_baixa_qualidade_de_dado` (
  `projeto_id` STRING NOT NULL,
  `projeto_nome` STRING,
  `item_id_viu2` INT64 NOT NULL,
  `item_id_globocorp` INT64 NOT NULL,
  `quantidade_passagens` INT64 NOT NULL,
  `status_atual` STRING,
  `cadastro_capturado_em` TIMESTAMP NOT NULL,
  `corte_historico_utc` TIMESTAMP NOT NULL,
  `marca` STRING,
  `talento` STRING,
  `eh_interveniencia` BOOL,
  `cadastro_atual_json` STRING NOT NULL,
  `versao_regra` STRING NOT NULL,
  `motivos_json` STRING NOT NULL,
  `primeiro_status_conhecido` STRING,
  `primeira_entrada_observada_utc` TIMESTAMP,
  `evidencias_passagens_json` STRING NOT NULL
) CLUSTER BY projeto_id;
