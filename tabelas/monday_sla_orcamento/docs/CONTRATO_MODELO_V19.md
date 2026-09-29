# Contrato do modelo v19 (`modelo-v20-1`)

Gerado por `scripts/generate_v19_docs.py`. Regras de negócio: nota do projeto (R1–R26) e
`src/monday_sla_orcamento/modelo_v19.py`. Horas úteis: seg–sex, 10–13h e 14–19h, America/Sao_Paulo.

## `monday_sla_projeto`

**Pergunta:** Quanto tempo levamos para orçar e entregar cada projeto?

**Chave:** `projeto_id` · cluster `situacao_atual`, `marca`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `projeto_id` | STRING | sim |
| `projeto_nome` | STRING |  |
| `conta_origem` | STRING | sim |
| `item_id_viu2` | INTEGER |  |
| `item_id_globocorp` | INTEGER |  |
| `entrada_utc` | TIMESTAMP | sim |
| `mes_entrada` | DATE | sim |
| `situacao_atual` | STRING | sim |
| `status_atual` | STRING |  |
| `primeira_entrega_utc` | TIMESTAMP |  |
| `ultima_entrega_utc` | TIMESTAMP |  |
| `quantidade_entregas` | INTEGER | sim |
| `quantidade_retrabalhos` | INTEGER | sim |
| `tempo_orcamento_horas_uteis` | FLOAT |  |
| `tempo_orcamento_horas_corridas` | FLOAT |  |
| `tempo_ate_primeira_entrega_horas_uteis` | FLOAT |  |
| `bruto_ate_primeira_entrega_horas_uteis` | FLOAT |  |
| `espera_marca_horas_uteis` | FLOAT |  |
| `standby_horas_uteis` | FLOAT |  |
| `resposta_cliente_horas_uteis` | FLOAT |  |
| `completo` | BOOLEAN | sim |
| `contem_estimativa` | BOOLEAN | sim |
| `nasceu_de_copia` | BOOLEAN | sim |
| `projeto_relacionado` | STRING |  |
| `marca` | STRING |  |
| `talento` | STRING |  |
| `eh_interveniencia` | BOOLEAN |  |
| `tipo_input` | STRING |  |
| `tipo_projeto` | STRING |  |
| `responsavel` | STRING |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_ciclo`

**Pergunta:** Como foi cada entrega e cada retrabalho?

**Chave:** `ciclo_id` · cluster `projeto_id`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `ciclo_id` | STRING | sim |
| `projeto_id` | STRING | sim |
| `numero_ciclo` | INTEGER | sim |
| `tipo_ciclo` | STRING | sim |
| `inicio_utc` | TIMESTAMP | sim |
| `fim_utc` | TIMESTAMP |  |
| `situacao` | STRING | sim |
| `trabalho_horas_uteis` | FLOAT |  |
| `trabalho_horas_corridas` | FLOAT |  |
| `espera_marca_horas_uteis` | FLOAT |  |
| `standby_horas_uteis` | FLOAT |  |
| `bruto_horas_uteis` | FLOAT |  |
| `passagens_trabalho` | INTEGER | sim |
| `completo` | BOOLEAN | sim |
| `contem_estimativa` | BOOLEAN | sim |
| `interval_id_entrega` | STRING |  |
| `mes_fim` | DATE |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_passagem`

**Pergunta:** Base comum: cada passagem por status, com origem da duração.

**Chave:** `interval_id` · cluster `projeto_id`, `status_nome`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `interval_id` | STRING | sim |
| `projeto_id` | STRING | sim |
| `ordem` | INTEGER | sim |
| `status_nome` | STRING |  |
| `categoria` | STRING | sim |
| `ciclo_id` | STRING |  |
| `conta_no_tempo_orcamento` | BOOLEAN | sim |
| `ignorada` | BOOLEAN | sim |
| `motivo_ignorada` | STRING |  |
| `conta_origem` | STRING | sim |
| `inicio_utc` | TIMESTAMP | sim |
| `saida_observada_utc` | TIMESTAMP |  |
| `fim_referencia_utc` | TIMESTAMP |  |
| `origem_duracao` | STRING | sim |
| `horas_uteis` | FLOAT |  |
| `horas_corridas` | FLOAT |  |
| `mes_inicio` | DATE | sim |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_tempo_status`

**Pergunta:** Quanto tempo cada projeto ficou em cada status?

**Chave:** `projeto_id`, `status_nome`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `projeto_id` | STRING | sim |
| `status_nome` | STRING | sim |
| `categoria` | STRING | sim |
| `visitas` | INTEGER | sim |
| `passagens` | INTEGER | sim |
| `horas_uteis` | FLOAT |  |
| `horas_corridas` | FLOAT |  |
| `completo` | BOOLEAN | sim |
| `contem_estimativa` | BOOLEAN | sim |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_resposta_cliente`

**Pergunta:** Quanto o cliente demora para responder, e o que ele fez?

**Chave:** `interval_id`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `interval_id` | STRING | sim |
| `projeto_id` | STRING | sim |
| `numero_entrega` | INTEGER | sim |
| `inicio_utc` | TIMESTAMP | sim |
| `proxima_acao_utc` | TIMESTAMP |  |
| `desfecho` | STRING | sim |
| `status_seguinte` | STRING |  |
| `conta_como_resposta` | BOOLEAN | sim |
| `horas_uteis` | FLOAT |  |
| `dias_corridos` | INTEGER |  |
| `origem_duracao` | STRING | sim |
| `mes_inicio` | DATE | sim |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_em_andamento`

**Pergunta:** O que está aberto agora, há quanto tempo, e com qual alerta?

**Chave:** `projeto_id`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `projeto_id` | STRING | sim |
| `projeto_nome` | STRING |  |
| `situacao_atual` | STRING | sim |
| `status_atual` | STRING |  |
| `no_status_desde_utc` | TIMESTAMP | sim |
| `horas_uteis_no_status` | FLOAT | sim |
| `numero_ciclo_atual` | INTEGER |  |
| `horas_uteis_desde_entrada` | FLOAT | sim |
| `referencia_atencao_horas` | FLOAT |  |
| `referencia_critico_horas` | FLOAT |  |
| `nivel_alerta` | STRING | sim |
| `responsavel` | STRING |  |
| `marca` | STRING |  |
| `talento` | STRING |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_referencia_status`

**Pergunta:** Qual o tempo de referência (SLA) de cada status?

**Chave:** `status_nome`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `status_nome` | STRING | sim |
| `categoria` | STRING | sim |
| `passagens_observadas` | INTEGER | sim |
| `p50_horas_uteis` | FLOAT |  |
| `p80_horas_uteis` | FLOAT |  |
| `p90_horas_uteis` | FLOAT |  |
| `referencia_atencao_horas` | FLOAT |  |
| `referencia_critico_horas` | FLOAT |  |
| `janela_inicio` | DATE | sim |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_gargalo_mensal`

**Pergunta:** Onde o tempo se acumula, mês a mês?

**Chave:** `mes`, `status_nome`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `mes` | DATE | sim |
| `status_nome` | STRING | sim |
| `categoria` | STRING | sim |
| `passagens` | INTEGER | sim |
| `projetos` | INTEGER | sim |
| `horas_uteis_total` | FLOAT |  |
| `horas_uteis_p50` | FLOAT |  |
| `horas_uteis_p80` | FLOAT |  |
| `passagens_sem_duracao` | INTEGER | sim |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_kpi_mensal`

**Pergunta:** Como estamos no mês (visão executiva)?

**Chave:** `mes`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `mes` | DATE | sim |
| `projetos_iniciados` | INTEGER | sim |
| `entregas` | INTEGER | sim |
| `projetos_primeira_entrega` | INTEGER | sim |
| `tempo_orcamento_p50_horas_uteis` | FLOAT |  |
| `tempo_orcamento_p80_horas_uteis` | FLOAT |  |
| `pct_projetos_com_retrabalho` | FLOAT |  |
| `pedidos_de_ajuste` | INTEGER | sim |
| `resposta_ajuste_p50_horas_uteis` | FLOAT |  |
| `encerrados_automaticos` | INTEGER | sim |
| `decisoes_registradas` | INTEGER | sim |
| `erros_preenchimento` | INTEGER | sim |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

**Leitura das medidas de tempo:** `tempo_orcamento_p50_horas_uteis` e `tempo_orcamento_p80_horas_uteis` medem o trabalho **até a 1ª entrega** dos projetos que tiveram a 1ª entrega naquele mês, sem os ajustes posteriores. O tempo total com retrabalho está em `monday_sla_projeto.tempo_orcamento_horas_uteis`. Decisão de 29/09/2026: manter a medida mensal como tempo até a 1ª entrega.

## `monday_sla_qualidade`

**Pergunta:** Quem ficou fora do cálculo, e por quê?

**Chave:** `chave`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `chave` | STRING | sim |
| `projeto_id` | STRING |  |
| `item_id_viu2` | INTEGER |  |
| `item_id_globocorp` | INTEGER |  |
| `projeto_nome` | STRING |  |
| `situacao_calculo` | STRING | sim |
| `motivos_json` | STRING | sim |
| `conta_origem` | STRING |  |
| `quantidade_passagens` | INTEGER | sim |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_erro_preenchimento`

**Pergunta:** Quais erros de preenchimento aconteceram (uma linha por erro)?

**Chave:** `erro_id` · cluster `tipo_erro`, `responsavel`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `erro_id` | STRING | sim |
| `projeto_id` | STRING |  |
| `item_id_globocorp` | INTEGER |  |
| `projeto_nome` | STRING |  |
| `tipo_erro` | STRING | sim |
| `gravidade` | STRING | sim |
| `descricao` | STRING | sim |
| `status_nome` | STRING |  |
| `ocorrido_em_utc` | TIMESTAMP |  |
| `mes` | DATE |  |
| `responsavel` | STRING |  |
| `conta_origem` | STRING |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_qualidade_preenchimento`

**Pergunta:** Como está o preenchimento por mês e por responsável?

**Chave:** `mes`, `responsavel`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `mes` | DATE | sim |
| `responsavel` | STRING | sim |
| `projetos_iniciados` | INTEGER | sim |
| `projetos_com_erro` | INTEGER | sim |
| `pct_projetos_sem_erro` | FLOAT |  |
| `erros` | INTEGER | sim |
| `erros_graves` | INTEGER | sim |
| `tipos_json` | STRING | sim |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_dim_status`

**Pergunta:** Quais status existem, como contam e quanto são usados?

**Chave:** `status_nome`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `status_nome` | STRING | sim |
| `categoria` | STRING | sim |
| `conta_no_tempo_orcamento` | BOOLEAN | sim |
| `eh_entrega` | BOOLEAN | sim |
| `eh_terminal` | BOOLEAN | sim |
| `etapa` | INTEGER |  |
| `no_quadro_atual` | BOOLEAN | sim |
| `passagens_total` | INTEGER | sim |
| `itens_total` | INTEGER | sim |
| `passagens_12_meses` | INTEGER | sim |
| `passagens_ano_atual` | INTEGER | sim |
| `primeiro_uso_utc` | TIMESTAMP |  |
| `ultimo_uso_utc` | TIMESTAMP |  |
| `versao_regra` | STRING | sim |

## `monday_sla_item_duplicado`

**Pergunta:** Quais itens foram duplicados de outro orçamento (fora do SLA, para estudo)?

**Chave:** `projeto_id`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `projeto_id` | STRING | sim |
| `item_id_globocorp` | INTEGER |  |
| `projeto_nome` | STRING |  |
| `status_copiado` | STRING |  |
| `entrada_utc` | TIMESTAMP | sim |
| `mes_entrada` | DATE | sim |
| `status_atual` | STRING |  |
| `quantidade_entregas` | INTEGER | sim |
| `primeira_entrega_utc` | TIMESTAMP |  |
| `trabalho_horas_uteis` | FLOAT |  |
| `trajeto` | STRING | sim |
| `projeto_relacionado` | STRING |  |
| `projeto_relacionado_nome` | STRING |  |
| `responsavel` | STRING |  |
| `marca` | STRING |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_standby`

**Pergunta:** Quais projetos estão parados em Standby agora, e há quanto tempo?

**Chave:** `projeto_id`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `projeto_id` | STRING | sim |
| `projeto_nome` | STRING |  |
| `em_standby_desde_utc` | TIMESTAMP | sim |
| `dias_corridos_parado` | INTEGER | sim |
| `horas_uteis_parado` | FLOAT | sim |
| `status_anterior` | STRING |  |
| `quantidade_entregas` | INTEGER | sim |
| `acima_do_limite` | BOOLEAN | sim |
| `responsavel` | STRING |  |
| `marca` | STRING |  |
| `talento` | STRING |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_dim_calendario`

**Pergunta:** Quais dias são úteis e quantas horas úteis cada um tem?

**Chave:** `data`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `data` | DATE | sim |
| `ano` | INTEGER | sim |
| `mes` | INTEGER | sim |
| `trimestre` | INTEGER | sim |
| `semana_iso` | STRING | sim |
| `dia_semana` | INTEGER | sim |
| `eh_dia_util` | BOOLEAN | sim |
| `eh_feriado` | BOOLEAN | sim |
| `nome_feriado` | STRING |  |
| `horas_uteis_dia` | FLOAT | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_projeto_diario`

**Pergunta:** Como cada projeto evoluiu dia a dia (base de previsão/ML)?

**Chave:** `projeto_id`, `data` · partição mensal por `data`; cluster `projeto_id`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `projeto_id` | STRING | sim |
| `data` | DATE | sim |
| `status_fim_do_dia` | STRING |  |
| `categoria` | STRING |  |
| `situacao_no_dia` | STRING | sim |
| `entregas_ate_o_dia` | INTEGER | sim |
| `tempo_orcamento_acumulado_horas_uteis` | FLOAT |  |
| `horas_uteis_desde_entrada` | FLOAT | sim |
| `eh_dia_util` | BOOLEAN | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_projeto_pool`

**Pergunta:** Quanto tempo levam os projetos com squad ou vários talentos (pool, fora do SLA oficial)?

**Chave:** `projeto_id`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `projeto_id` | STRING | sim |
| `projeto_nome` | STRING |  |
| `conta_origem` | STRING | sim |
| `item_id_viu2` | INTEGER |  |
| `item_id_globocorp` | INTEGER |  |
| `motivo_pool` | STRING | sim |
| `talentos_json` | STRING |  |
| `entrada_utc` | TIMESTAMP | sim |
| `mes_entrada` | DATE | sim |
| `situacao_atual` | STRING | sim |
| `status_atual` | STRING |  |
| `quantidade_entregas` | INTEGER | sim |
| `quantidade_retrabalhos` | INTEGER | sim |
| `tempo_orcamento_horas_uteis` | FLOAT |  |
| `tempo_ate_primeira_entrega_horas_uteis` | FLOAT |  |
| `espera_marca_horas_uteis` | FLOAT |  |
| `standby_horas_uteis` | FLOAT |  |
| `resposta_cliente_horas_uteis` | FLOAT |  |
| `completo` | BOOLEAN | sim |
| `marca` | STRING |  |
| `tipo_input` | STRING |  |
| `responsavel` | STRING |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_sla_sem_entrada`

**Pergunta:** Quais projetos não começaram por Entrada, e qual foi a trajetória completa de cada um?

**Chave:** `projeto_id`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `projeto_id` | STRING | sim |
| `projeto_nome` | STRING |  |
| `conta_origem` | STRING | sim |
| `item_id_viu2` | INTEGER |  |
| `item_id_globocorp` | INTEGER |  |
| `primeiro_status` | STRING |  |
| `primeiro_status_utc` | TIMESTAMP |  |
| `status_atual` | STRING |  |
| `passa_por_entrada_depois` | BOOLEAN | sim |
| `quantidade_passagens` | INTEGER | sim |
| `quantidade_entregas` | INTEGER | sim |
| `horas_uteis_conhecidas` | FLOAT |  |
| `trajeto` | STRING | sim |
| `trajeto_json` | STRING | sim |
| `marca` | STRING |  |
| `talento` | STRING |  |
| `responsavel` | STRING |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_dim_talento`

**Pergunta:** Quais talentos aparecem no quadro, com que grafias, se são exclusivos e quantas vezes foram usados?

**Chave:** `chave_talento`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `chave_talento` | STRING | sim |
| `talento_nome` | STRING | sim |
| `variantes_json` | STRING | sim |
| `quantidade_variantes` | INTEGER | sim |
| `eh_exclusivo` | BOOLEAN | sim |
| `usos_exclusivo` | INTEGER | sim |
| `usos_interveniencia` | INTEGER | sim |
| `itens_quadro` | INTEGER | sim |
| `projetos_no_sla` | INTEGER | sim |
| `projetos_pool` | INTEGER | sim |
| `possivel_duplicata_de` | STRING |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |

## `monday_dim_marca`

**Pergunta:** Quais marcas aparecem no quadro, com que grafias e quantas vezes foram usadas?

**Chave:** `chave_marca`

| Coluna | Tipo | Obrigatória |
| :--- | :--- | :-: |
| `chave_marca` | STRING | sim |
| `marca_nome` | STRING | sim |
| `variantes_json` | STRING | sim |
| `quantidade_variantes` | INTEGER | sim |
| `itens_quadro` | INTEGER | sim |
| `projetos_no_sla` | INTEGER | sim |
| `possivel_duplicata_de` | STRING |  |
| `corte_utc` | TIMESTAMP | sim |
| `versao_regra` | STRING | sim |
