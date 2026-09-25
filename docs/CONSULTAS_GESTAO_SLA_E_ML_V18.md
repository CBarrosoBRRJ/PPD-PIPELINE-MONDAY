# Consultas de gestao do orçamento e roteiro de ML — v18

Estado de referência: primeira publicação v18 verificada em 25/09/2026. Estas
consultas são **somente leitura**, em GoogleSQL, localização BigQuery `US`.
Copie **um bloco SQL por vez no editor SQL do BigQuery/DBeaver**; não cole
`SELECT` diretamente no Bash. No Cloud Shell, use `bq query` com
`--use_legacy_sql=false`, `--location=US` e limite de cobrança apropriado.
Não foram executadas no GCP nesta revisão do documento: conferir a primeira
linha, contagens e custo estimado no seu ambiente antes de divulgar resultados.
As contagens de 25/09 (7.625 passagens, 1.583 projetos, 1.685 ciclos e 4 na
fila selecionada) são um recibo datado, não metas nem números fixos.

## Antes de usar os números

| Fonte | Grão e pergunta adequada | Limite |
|---|---|---|
| `monday_sla_orcamento` | Uma passagem por status; trajetória, tempos e contexto atual do projeto. | População selecionada; passagem ≠ projeto ≠ permanência contínua. |
| `monday_ciclos_orcamento` | Uma tentativa de orçamento, inclusive reabertura; entrega e tempo operacional. | Usar `kpi_entrega_observada` para prazo comprovado; aberto/estimado separado. |
| `monday_fila_precificacao` | Um projeto elegível ainda só em Entrada. | Subconjunto do SLA, não fila inteira do board. |
| `monday_sla_baixa_qualidade_de_dado` | Um projeto com motivo/evidência para investigação. | Pode coexistir com SLA; não somar as populações. |
| `monday_backlog_agenciamento_2026` | Um item atual do quadro Globocorp, inclusive fora do SLA. | Retrato atual, não histórico de status nem prova de demanda exclusivamente de orçamento. |
| `monday_talentos_exclusivos` | Um item do cadastro atual de talentos. | Não unir por semelhança de nome ao SLA; não é histórico de demanda. |
| `monday_sla_orcamento_viu2` e `monday_sla_orcamento_globocorp` | Passagens de origem para auditar uso de status e lacunas. | Não somar seus tempos à consolidada; a principal já reconcilia o projeto. |
| `monday_log_viu2` | Evidência bruta congelada de mudanças. | Log não é passagem nem ciclo; usar para auditoria, não contagem direta de SLA. |

Horário útil do pipeline: seg–sex 10–13h e 14–19h, São Paulo, com calendário
e feriados versionados. É **permanência no status durante o expediente**, não
horas efetivamente trabalhadas. `sla_origem_duracao='observada'` identifica
uma saída medida; `estimada_migracao`, `idade_aberta_no_corte` e `indisponivel`
não entram silenciosamente nas médias observadas. Marca, talento, tipo de
input e listas `cadastro_atual_*` descrevem o **cadastro atual**, inclusive
quando aparecem numa passagem antiga ViU2. Filtre por corte/período quando
comparar rodadas, mas não esconda o começo da trajetória no drill-through.

## 1. Quantas vezes cada status foi usado?

Para decidir se um status do Monday ainda é necessário, comece pelas **duas
fontes completas**. Separe ambientes: o mesmo rótulo pode ter significado
operacional diferente e a consolidação exclui parte dos projetos. Uma linha de
origem é uma passagem registrada; ausência de uso não prova que um status pode
ser removido do quadro sem consultar a equipe.

```sql
WITH historico AS (
  SELECT 'viu2' AS ambiente, status_nome, item_id, interval_id
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento_viu2`
  UNION ALL
  SELECT 'globocorp', status_nome, item_id, interval_id
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento_globocorp`
)
SELECT ambiente, COALESCE(NULLIF(TRIM(status_nome), ''), '(sem status)') AS status,
  COUNT(*) AS passagens_registradas,
  COUNT(DISTINCT item_id) AS itens_distintos,
  COUNT(DISTINCT interval_id) AS intervalos_distintos
FROM historico
GROUP BY 1, 2
ORDER BY ambiente, passagens_registradas DESC, status;
```

Na população final, `passagens` conta cada registro; `permanencias` evita
contar duas vezes a continuação do mesmo status na fronteira ViU2/Globocorp.
`projetos` responde quantos projetos chegaram à etapa.

```sql
SELECT sla_categoria_tempo, status_nome,
  COUNT(*) AS passagens,
  COUNT(DISTINCT COALESCE(sla_grupo_permanencia_id, interval_id)) AS permanencias,
  COUNT(DISTINCT projeto_id) AS projetos,
  COUNTIF(ambiente_origem = 'viu2') AS passagens_viu2,
  COUNTIF(ambiente_origem = 'globocorp') AS passagens_globocorp
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
GROUP BY sla_categoria_tempo, status_nome
ORDER BY passagens DESC, status_nome;
```

## 2. Média e mediana por status: candidatos a gargalo

Apenas durações **observadas e encerradas**. Mostra todos os tipos de status,
mas compare operacional, Feedback, terceiros e Standby **separadamente**.
Entrada é espera para começar, não esforço; uma média alta não prova a causa.
Mediana abaixo é exata (`PERCENTILE_CONT`); P90 é aproximação estatística.

```sql
WITH medidas AS (
  SELECT projeto_id, status_nome, sla_categoria_tempo,
    sla_horas_corridas, sla_horas_uteis,
    PERCENTILE_CONT(sla_horas_uteis, 0.5) OVER (
      PARTITION BY sla_categoria_tempo, status_nome
    ) AS mediana_horas_uteis
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  WHERE sla_origem_duracao = 'observada'
    AND sla_horas_uteis IS NOT NULL
)
SELECT sla_categoria_tempo, status_nome,
  COUNT(*) AS passagens_medidas,
  COUNT(DISTINCT projeto_id) AS projetos,
  ROUND(SUM(sla_horas_uteis), 2) AS exposicao_horas_uteis,
  ROUND(AVG(sla_horas_corridas), 2) AS media_horas_corridas,
  ROUND(AVG(sla_horas_uteis), 2) AS media_horas_uteis,
  ROUND(ANY_VALUE(mediana_horas_uteis), 2) AS mediana_horas_uteis,
  ROUND(APPROX_QUANTILES(sla_horas_uteis, 100)[OFFSET(90)], 2)
    AS p90_aproximado_horas_uteis
FROM medidas
GROUP BY sla_categoria_tempo, status_nome
ORDER BY exposicao_horas_uteis DESC;
```

Olhe exposição total **e** frequência: uma etapa rara e longa pode impactar
menos o fluxo que uma etapa moderada repetida muitas vezes. Não some medianas
de status para obter a mediana do ciclo.

## 3. Tempo aguardando retorno do cliente ou de terceiros

`feedback` é espera **depois de entregar** o orçamento; `terceiros` é Retorno
Marca/Executivo **antes/durante** a elaboração. A consulta mostra ambas sem
misturá-las no mesmo indicador. O fim da passagem é uma **aproximação da
resposta**, não prova de que o cliente respondeu naquele instante; um evento
explícito de resposta resolveria essa limitação. A média inclui só esperas com saída observada;
abertas, estimadas e indisponíveis ficam expostas em colunas próprias.

```sql
SELECT sla_categoria_tempo,
  COUNT(*) AS passagens_totais,
  COUNTIF(sla_origem_duracao = 'observada') AS esperas_observadas,
  COUNTIF(sla_origem_duracao = 'estimada_migracao') AS esperas_estimadas,
  COUNTIF(sla_origem_duracao = 'idade_aberta_no_corte') AS abertas_no_corte,
  COUNTIF(sla_origem_duracao = 'indisponivel') AS duracao_indisponivel,
  ROUND(AVG(IF(sla_origem_duracao = 'observada',
    sla_horas_corridas, NULL)), 2) AS media_horas_corridas_observadas,
  ROUND(AVG(IF(sla_origem_duracao = 'observada',
    sla_horas_uteis, NULL)), 2) AS media_horas_uteis_observadas
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
WHERE sla_categoria_tempo IN ('feedback', 'terceiros')
GROUP BY sla_categoria_tempo
ORDER BY sla_categoria_tempo;
```

## 4. Tempo para entregar um orçamento ao mercado

O marco de entrega observado é a entrada em **Aguardando Feedback**. Uma linha
por ciclo; primeira elaboração e revisões são resultados distintos. Use apenas
`kpi_entrega_observada=TRUE`. `janela_corrida` vai do início do ciclo até esse
marco e inclui esperas; `operacao_horas_uteis` exclui Feedback posterior,
Retorno Marca/Executivo e Standby. Nenhuma das duas mede esforço individual.

```sql
WITH entregas AS (
  SELECT projeto_id, tipo_ciclo, inicio_utc, fim_utc,
    operacao_horas_corridas, operacao_horas_uteis,
    TIMESTAMP_DIFF(fim_utc, inicio_utc, SECOND) / 3600.0
      AS janela_horas_corridas,
    PERCENTILE_CONT(operacao_horas_uteis, 0.5) OVER (
      PARTITION BY tipo_ciclo
    ) AS mediana_operacao_horas_uteis
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
  WHERE kpi_entrega_observada IS TRUE
)
SELECT tipo_ciclo,
  COUNT(*) AS entregas_observadas,
  COUNT(DISTINCT projeto_id) AS projetos,
  ROUND(AVG(janela_horas_corridas), 2) AS media_janela_horas_corridas,
  ROUND(AVG(operacao_horas_corridas), 2) AS media_operacao_horas_corridas,
  ROUND(AVG(operacao_horas_uteis), 2) AS media_operacao_horas_uteis,
  ROUND(ANY_VALUE(mediana_operacao_horas_uteis), 2)
    AS mediana_operacao_horas_uteis,
  ROUND(APPROX_QUANTILES(operacao_horas_uteis, 100)[OFFSET(90)], 2)
    AS p90_aproximado_operacao_horas_uteis
FROM entregas
GROUP BY tipo_ciclo
ORDER BY tipo_ciclo;
```

`entregas_observadas` conta envios/ciclos, não projetos únicos. Um projeto pode
ter primeiro envio e novas revisões. Sem meta pactuada, P90 não é “atraso”.

## 5. Responsáveis associados às etapas demoradas — não autoria histórica

O cadastro tem **todas** as colunas atuais: Orçamento, Talent Manager, GP,
Conteúdo, Produção e Audiência. Os arrays guardam ID e nome de pessoas/equipes.
Esta consulta associa pessoas **atualmente cadastradas** a projetos que tiveram
permanência operacional observada. Não prova quem executou aquela passagem,
quem causou a demora, nem produtividade ajustada por complexidade. Uma etapa
com várias pessoas/áreas atribui o tempo inteiro a cada associação: **não
some os totais entre responsáveis**. Use como lista para revisão de casos.

```sql
WITH sla AS (
  SELECT * FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
), cadastro AS (
  SELECT projeto_id, cadastro_atual_orcamento_json,
    cadastro_atual_talent_manager_json, cadastro_atual_gp_json,
    cadastro_atual_conteudo_json, cadastro_atual_producao_json,
    cadastro_atual_audiencia_json
  FROM sla
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY projeto_id
    ORDER BY cadastro_atual_capturado_em DESC, interval_id DESC
  ) = 1
), pessoas AS (
  SELECT DISTINCT cadastro.projeto_id, coluna.area,
    JSON_VALUE(pessoa, '$.id') AS pessoa_id,
    COALESCE(NULLIF(JSON_VALUE(pessoa, '$.nome'), ''),
      CONCAT('ID ', JSON_VALUE(pessoa, '$.id'))) AS nome_atual
  FROM cadastro
  CROSS JOIN UNNEST([
    STRUCT('Orcamento' AS area, cadastro_atual_orcamento_json AS pessoas_json),
    STRUCT('Talent Manager' AS area, cadastro_atual_talent_manager_json AS pessoas_json),
    STRUCT('GP' AS area, cadastro_atual_gp_json AS pessoas_json),
    STRUCT('Conteudo' AS area, cadastro_atual_conteudo_json AS pessoas_json),
    STRUCT('Producao' AS area, cadastro_atual_producao_json AS pessoas_json),
    STRUCT('Audiencia' AS area, cadastro_atual_audiencia_json AS pessoas_json)
  ]) AS coluna
  CROSS JOIN UNNEST(IFNULL(
    JSON_QUERY_ARRAY(coluna.pessoas_json), ARRAY<STRING>[]
  )) AS pessoa
  WHERE JSON_VALUE(pessoa, '$.tipo') = 'person'
    AND JSON_VALUE(pessoa, '$.id') IS NOT NULL
), projeto_etapa AS (
  SELECT projeto_id, status_nome,
    COUNT(*) AS passagens_observadas,
    SUM(sla_horas_uteis) AS horas_uteis_observadas
  FROM sla
  WHERE sla_categoria_tempo = 'operacao'
    AND sla_origem_duracao = 'observada'
    AND sla_horas_uteis IS NOT NULL
  GROUP BY projeto_id, status_nome
)
SELECT e.status_nome, p.area, p.pessoa_id, p.nome_atual,
  COUNT(DISTINCT e.projeto_id) AS projetos_associados,
  SUM(e.passagens_observadas) AS passagens_desses_projetos,
  ROUND(AVG(e.horas_uteis_observadas), 2)
    AS media_horas_uteis_por_projeto,
  ROUND(SUM(e.horas_uteis_observadas), 2)
    AS exposicao_associada_nao_aditiva
FROM projeto_etapa e
JOIN pessoas p USING(projeto_id)
GROUP BY e.status_nome, p.area, p.pessoa_id, p.nome_atual
ORDER BY e.status_nome, media_horas_uteis_por_projeto DESC;
```

Antes de apontar um ofensor, conferir casos, carga/WIP, prioridade, complexidade,
dependências externas e **atribuição histórica**. Hoje não existe base suficiente
para um ranking causal ou disciplinar de indivíduos.

## 6. Quais marcas mais demoram a dar Feedback?

Uma passagem `feedback` terminada e observada mede espera após envio, usando
a próxima transição como aproximação de retorno, não confirmação da resposta.
A marca
vem do cadastro **atual** do projeto. Ordenar só pela média pode destacar
marcas com uma ocorrência; leia sempre `esperas` e `projetos` junto. Não
atribuir à marca passagens com espera estimada ou ainda aberta.

```sql
WITH sla AS (
  SELECT * FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
), projeto AS (
  SELECT projeto_id,
    COALESCE(NULLIF(TRIM(cadastro_atual_marca), ''), '(marca nao informada)')
      AS marca_atual
  FROM sla
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY projeto_id
    ORDER BY cadastro_atual_capturado_em DESC, interval_id DESC
  ) = 1
), esperas AS (
  SELECT p.marca_atual, s.projeto_id, s.sla_horas_corridas,
    s.sla_horas_uteis,
    PERCENTILE_CONT(s.sla_horas_corridas, 0.5) OVER (
      PARTITION BY p.marca_atual
    ) AS mediana_horas_corridas
  FROM sla s
  JOIN projeto p USING(projeto_id)
  WHERE s.sla_categoria_tempo = 'feedback'
    AND s.sla_origem_duracao = 'observada'
    AND s.sla_horas_corridas IS NOT NULL
)
SELECT marca_atual, COUNT(*) AS esperas_observadas,
  COUNT(DISTINCT projeto_id) AS projetos,
  ROUND(AVG(sla_horas_corridas), 2) AS media_horas_corridas,
  ROUND(ANY_VALUE(mediana_horas_corridas), 2) AS mediana_horas_corridas,
  ROUND(AVG(sla_horas_uteis), 2) AS media_horas_uteis
FROM esperas
GROUP BY marca_atual
ORDER BY media_horas_corridas DESC, esperas_observadas DESC;
```

Para análise de negociação, repetir com `sla_categoria_tempo='terceiros'`
mostra Retorno Marca/Executivo antes da entrega, **não** a mesma espera.

## 7. Quantos projetos estão na fila aguardando orçamento?

Duas respostas legítimas: fila **selecionada** de projetos com apenas Entrada
e cadastro consistente, e todos os itens **atualmente** em Entrada no backlog.
Não some os dois recortes: o primeiro está dentro do segundo quando o item
ainda permanece no board. A fila não inclui projetos já em elaboração.

```sql
SELECT 'fila_sla_selecionada' AS recorte,
  COUNT(DISTINCT projeto_id) AS unidades,
  MAX(cadastro_capturado_em) AS captura_mais_recente,
  ROUND(AVG(espera_horas_uteis), 2) AS media_espera_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_fila_precificacao`
UNION ALL
SELECT 'backlog_atual_em_entrada',
  COUNT(DISTINCT item_id), MAX(capturado_em), CAST(NULL AS FLOAT64)
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_backlog_agenciamento_2026`
WHERE board_id = 18429499488 AND status_nome = 'Entrada';
```

Para ação diária, listar a fila selecionada por idade, sem transformar NULL
em zero nem assumir meta de espera que ainda não foi pactuada:

```sql
SELECT projeto_id, projeto_nome, marca, talento, eh_interveniencia,
  entrada_fila_utc, espera_ate_utc, espera_horas_uteis
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_fila_precificacao`
ORDER BY espera_horas_uteis DESC, entrada_fila_utc
LIMIT 100;
```

## 8. Marcas que mais demandam orçamento

Uma linha **atual** por projeto elegível antes do join com ciclos. Projetos
medem demandas distintas; ciclos incluem revisões e não são novos projetos.
`entregas_observadas` é quantidade de ciclos com KPI aprovado, não faturamento.

```sql
WITH projeto AS (
  SELECT projeto_id,
    COALESCE(NULLIF(TRIM(cadastro_atual_marca), ''), '(marca nao informada)')
      AS marca_atual
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY projeto_id
    ORDER BY cadastro_atual_capturado_em DESC, interval_id DESC
  ) = 1
)
SELECT p.marca_atual,
  COUNT(DISTINCT p.projeto_id) AS projetos_que_demandaram,
  COUNT(c.ciclo_id) AS ciclos_incluindo_revisoes,
  COUNTIF(c.kpi_entrega_observada) AS entregas_observadas
FROM projeto p
LEFT JOIN `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento` c
  USING(projeto_id)
GROUP BY p.marca_atual
ORDER BY projetos_que_demandaram DESC, ciclos_incluindo_revisoes DESC;
```

O ranking cobre só a população do SLA. Para **todas as demandas atuais do
board**, contar `item_id` por `marca` no snapshot backlog e rotular como itens
atuais, não projetos históricos reconciliados. Padronizar aliases de marcas
com o negócio antes de unir grafias diferentes.

## 9. Talentos mais demandados

`talento_nome_atual` é o rótulo único aceito pelo escopo; `eh_interveniencia`
separa Interveniência de Talentos Exclusivos. Não juntar à tabela
`monday_talentos_exclusivos` por nome: ela é outro cadastro, sem chave de
projeto homologada para esse relacionamento.

```sql
WITH projeto AS (
  SELECT projeto_id,
    COALESCE(NULLIF(TRIM(talento_nome_atual), ''), '(talento nao informado)')
      AS talento_atual,
    eh_interveniencia
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY projeto_id
    ORDER BY cadastro_atual_capturado_em DESC, interval_id DESC
  ) = 1
)
SELECT p.talento_atual,
  CASE p.eh_interveniencia
    WHEN TRUE THEN 'Interveniencia'
    WHEN FALSE THEN 'Talento Exclusivo'
    ELSE 'origem nao classificada'
  END AS origem_talento,
  COUNT(DISTINCT p.projeto_id) AS projetos_que_demandaram,
  COUNT(c.ciclo_id) AS ciclos_incluindo_revisoes,
  COUNTIF(c.kpi_entrega_observada) AS entregas_observadas
FROM projeto p
LEFT JOIN `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento` c
  USING(projeto_id)
GROUP BY p.talento_atual, origem_talento
ORDER BY projetos_que_demandaram DESC, ciclos_incluindo_revisoes DESC;
```

Talentos fora do escopo (Squad, múltiplos, colunas ambíguas ou vazias) não
entram nesse ranking; consulte o backlog e a qualidade antes de concluir que
não houve demanda por eles.

## 10. Tipo de entrada: de onde vêm os pedidos?

O backlog traz `tipo_input` **atual** de todos os itens capturados. Isso é o
melhor ranking disponível para canal/local do pedido, mas não é um evento
imutável de criação. Não chamar `tipo_input` de geografia se os valores do
quadro representam modalidade, iniciativa ou origem comercial.

```sql
SELECT COALESCE(NULLIF(TRIM(tipo_input), ''), '(nao informado)')
    AS tipo_input_atual,
  COUNT(DISTINCT item_id) AS itens_atuais,
  COUNTIF(status_nome = 'Entrada') AS itens_atuais_em_entrada,
  MAX(capturado_em) AS captura_mais_recente
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_backlog_agenciamento_2026`
WHERE board_id = 18429499488
GROUP BY tipo_input_atual
ORDER BY itens_atuais DESC, tipo_input_atual;
```

Se a pergunta for **somente pelos projetos aceitos no SLA**, use o recorte
abaixo. Os dois rankings diferem porque o SLA tem filtros de título, input,
talento, identidade e qualidade; não compare percentuais sem mostrar isso.

```sql
WITH projeto AS (
  SELECT projeto_id, cadastro_atual_tipo_input
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY projeto_id
    ORDER BY cadastro_atual_capturado_em DESC, interval_id DESC
  ) = 1
)
SELECT COALESCE(NULLIF(TRIM(cadastro_atual_tipo_input), ''),
    '(nao informado)') AS tipo_input_atual,
  COUNT(*) AS projetos_sla
FROM projeto
GROUP BY tipo_input_atual
ORDER BY projetos_sla DESC;
```

## 11. Cruzamentos adicionais úteis

**Cobertura e correção:** motivos de baixa qualidade por projeto, separando
quem ainda tem trecho aproveitável no SLA. Motivos coexistem; sua soma pode
exceder a quantidade de projetos únicos.

```sql
WITH motivos AS (
  SELECT q.projeto_id, motivo
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_baixa_qualidade_de_dado` q,
  UNNEST(JSON_VALUE_ARRAY(q.motivos_json)) AS motivo
), projetos_sla AS (
  SELECT DISTINCT projeto_id
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
)
SELECT m.motivo,
  COUNT(DISTINCT m.projeto_id) AS projetos_com_motivo,
  COUNT(DISTINCT IF(s.projeto_id IS NOT NULL, m.projeto_id, NULL))
    AS tambem_presentes_no_sla
FROM motivos m
LEFT JOIN projetos_sla s USING(projeto_id)
GROUP BY m.motivo
ORDER BY projetos_com_motivo DESC;
```

**Reaberturas e carga:** uma nova tentativa conta outro ciclo, não outro
projeto. Coorte por início não é throughput por entrega; ciclos recentes
podem continuar abertos, então não interprete a razão entregue/total como
taxa final de sucesso da coorte.

```sql
SELECT DATE_TRUNC(DATE(inicio_utc, 'America/Sao_Paulo'), MONTH)
    AS mes_de_inicio,
  COUNT(*) AS ciclos_iniciados,
  COUNT(DISTINCT projeto_id) AS projetos,
  COUNTIF(tipo_ciclo = 'revisao_reabertura') AS revisoes_iniciadas,
  COUNTIF(situacao = 'em_andamento') AS ciclos_ainda_abertos,
  COUNTIF(situacao = 'entregue') AS ciclos_entregues,
  COUNTIF(kpi_entrega_observada) AS entregas_com_tempo_observado
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
GROUP BY mes_de_inicio
ORDER BY mes_de_inicio;
```

## Indicadores para um painel de gestão

Separar cartões de **resultado**, **fluxo**, **demanda** e **confiança**. Para
cada série mostrar período, N, população, relógio (corridas/úteis), fração
estimada/indisponível e data do último corte. Não há meta de prazo pactuada;
não pintar vermelho por superar uma média histórica.

| Indicador | Cálculo e grão | Decisão apoiada | Condição atual |
|---|---|---|---|
| Entregas e P50/P90 operacional | Ciclos com `kpi_entrega_observada=TRUE`, por data de `fim_utc`; uma linha por ciclo. | Previsibilidade de entrega e cauda longa. | Disponível no escopo selecionado. |
| Espera do cliente | Passagens `feedback` observadas: média, P50 e P90; abertas/estimadas à parte. | Melhorar ritual de devolutiva e cobrança. | Disponível parcialmente. |
| Espera por briefing/terceiros | Passagens `terceiros` observadas, não misturar com Feedback. | Completar informações na entrada. | Disponível parcialmente. |
| Exposição por etapa e retornos | Soma de horas observadas por categoria/status; `sla_retorno_status` para repetição. | Escolher gargalo para investigar. | Retorno não prova defeito. |
| Fila e envelhecimento | Fila selecionada por `projeto_id` e horas úteis no corte; backlog total em Entrada à parte. | Priorizar triagem e não esquecer antigos. | Disponível com dois universos distintos. |
| Entradas, saídas e WIP | Projetos novos, ciclos entregues e ciclos abertos por período/corte. | Ver se a demanda supera a capacidade. | Comparar coortes e população com cautela. |
| Demanda por marca, talento e input | Projetos únicos no SLA; itens atuais no backlog como outro recorte. | Dimensionar cobertura e portfólio. | Segmentos são cadastro atual. |
| Qualidade e cobertura | Projetos excluídos, diagnósticos coexistentes, durações observadas/estimadas/indisponíveis. | Priorizar correção da origem. | Disponível; definir denominador antes de porcentagens. |

Indicador **ainda não medido**: esforço real, capacidade por pessoa, tempo de
handoff com dono/aceite, retrabalho por defeito, prazo contratual e retorno
financeiro. Permanência num status não substitui esses eventos. Para saber
se uma ação melhorou o processo, compare coortes/mix similares e acompanhe
volume, P90, reaberturas, qualidade e idade dos abertos como guardrails.

## Melhorias de controle e captura — propostas, sem alterar bases agora

1. **Dicionário dos status e marcos.** Aprovar significado, dono da etapa,
   categoria operacional/espera/terminal, transições permitidas e vigência do
   rótulo por ambiente. Registrar explicitamente `orcamento_enviado_em`,
   `feedback_recebido_em` e `orcamento_aceito_em`; hoje Aguardando Feedback é
   o marco operacional de envio, não aceite comercial certificado. Ganho:
   KPIs estáveis apesar de renomeação de status.
2. **Evento de atribuição histórica.** A cada mudança de responsável, registrar
   projeto, ciclo, papel/área, ID de pessoa ou equipe, início/fim de vigência,
   origem e motivo de transferência. Guardar a cardinalidade e não sobrescrever
   com cadastro atual. Ganho: medir handoff, carga e desempenho de células com
   contexto; ainda não inferir causalidade individual.
3. **Pedido na entrada.** Congelar no instante da solicitação marca, talento e
   origem do talento, `tipo_input`, canal/local real, prioridade, complexidade,
   prazo pactuado, completude do briefing e solicitante, com versões posteriores
   separadas. Ganho: denominador de demanda, segmentação temporal e features
   sem vazamento para ML. Não inventar esses valores a partir do cadastro de hoje.
4. **Motivo de espera, revisão e desfecho.** Distinguir ajuste solicitado pelo
   cliente, nova estratégia, erro de briefing, revisão de orçamento, alteração
   contratual, pausa planejada e cancelamento; permitir “não informado”.
   Registrar quem classificou e quando. Ganho: retrabalho evitável deixa de
   ser confundido com negociação normal.
5. **Capacidade e trabalho ativo.** Registrar disponibilidade planejada por
   equipe, WIP, início/fim de trabalho ou esforço apontado e prioridades da
   fila. Ganho: simular escala e identificar gargalos reais; hoje sabemos
   permanência, não capacidade nem touch-time. Não usar apontamento para
   vigilância individual sem governança aprovada.
6. **Histórico reproduzível no corte.** Guardar snapshots/eventos imutáveis
   com `projeto_id`, IDs nativos por ambiente, `ciclo_id`, `interval_id`,
   horário do evento, horário da captura, versão de calendário/regra e
   proveniência de cada campo. Correção posterior deve manter trilha de
   alteração e não mudar silenciosamente o que era conhecido no passado.
   Ganho: treino e auditoria “como era naquele dia”, sem vazamento temporal.
7. **Portões de qualidade contínua.** No relatório diário, mostrar cobertura
   do mapa ViU2↔Globocorp, Entrada comprovada, status desconhecido, lacunas,
   duplicidade, campos obrigatórios, proporção observada/estimada/indisponível,
   idade da captura e publicação/alerta. Correção no board deve reincluir o
   projeto na próxima rodada elegível; alerta não substitui correção.

Essas são sugestões de contrato/processo, **não autorização para criar tabelas,
coletar dados pessoais novos ou alterar o Monday agora**. Priorizar com a área,
privacidade/IAM e retenção antes de implementar. Na ordem prática: começar
com dicionário e eventos de entrega/feedback; depois atribuição histórica e
motivos; então capacidade e snapshots para modelagem.

## Modelos de ML e otimização: por quê, como e quando

Primeiro produzir as linhas-base (mediana/P90 por tipo de ciclo, regras de fila,
contagem semanal) e o painel de confiança. Nenhum modelo foi treinado ou
homologado por este arquivo. O histórico aceito é seletivo: 1.583 projetos no
recibo inicial, dos quais apenas 14 tinham um mesmo ciclo operacional nos dois
ambientes e todos esses 14 continham estimativa. Um modelo treinado com
`cadastro_atual_*` em ciclos antigos aprenderia informação futura. A validação
deve ser por **tempo e projeto**, com teste final posterior e não usado no
ajuste; pré-processamento aprendido só no treino. Esta restrição segue a
[orientação oficial do scikit-learn sobre vazamento](https://scikit-learn.org/stable/common_pitfalls.html)
e a [avaliação do BigQuery ML em dados não usados no treino](https://docs.cloud.google.com/bigquery/docs/evaluate-overview).

| Proposta e decisão | Alvo, dados e baseline | Candidato e avaliação | Ganho a comprovar / prontidão |
|---|---|---|---|
| **Faixa de prazo na entrada**: que intervalo prometer? | Alvo: horas úteis operacionais até o primeiro Feedback **observado**; features conhecidas na Entrada (tipo, complexidade, marca agrupada, calendário), nunca status final ou cadastro corrigido depois. Baseline: P50/P90 histórico por segmento com fallback global. | Regressão quantílica/gradient boosting apenas se superar baseline. MAE para P50, pinball loss P50/P90, cobertura do P90 perto de 90% e largura do intervalo, por período/segmento. | Melhor promessa e menos cobrança. Abertos não podem ser descartados sem analisar viés; precisa snapshot da Entrada e amostra suficiente no fluxo atual. |
| **Risco de demora do caso ativo**: quem revisar hoje? | Alvo: entrega observada nos próximos 2/5/10 dias úteis, com idade e status *no corte T*. Abertos no corte são censurados quando o estado é confiável; lacuna histórica não é censura válida. Baseline: taxa por status/idade e regra de fila. | Sobrevivência (Kaplan–Meier por classe, Cox regularizado; floresta apenas se houver volume). Avaliar Brier/calibração por horizonte, C-index/IPCW e `precision@K`, onde K é a capacidade diária de revisão humana. | Antecipar escalonamento sem gerar alertas inúteis. Requer cortes históricos imutáveis e rótulos/censura confiáveis. [Avaliação de sobrevivência](https://scikit-survival.readthedocs.io/en/stable/user_guide/evaluating-survival-models.html). |
| **Previsão de chegada e capacidade**: quantos pedidos na próxima semana? | Alvo: pedidos novos por semana e canal/área, idealmente no universo completo do board. Baseline sazonal (semana anterior/média móvel), sem multiplicar revisões por novos pedidos. | Série temporal ou regressão de contagem se vencer baseline em janelas futuras. MAE/WAPE por semana, erro de picos e cobertura de intervalo de previsão; conferir segmentos esparsos. | Planejar triagem e turnos. Snapshot atual isolado não reconstrói séries completas; precisa evento de criação confiável e tempo histórico suficiente. |
| **Risco de retrabalho evitável**: qual briefing revisar antes de produzir? | Alvo: revisão **por defeito** após envio, não toda reabertura. Baseline checklist de completude; features somente da Entrada. | Classificador calibrado; PR-AUC, recall e `precision@K` com capacidade de revisão, taxa de falso alerta e calibração por grupo. | Menos retrabalho sem barrar revisões legítimas. Bloqueado até haver motivo/aceite padronizado e confirmação humana do rótulo. [Calibração de probabilidades](https://scikit-learn.org/stable/modules/calibration.html). |
| **Simulação de fila e alocação**: que política reduz espera? | Chegadas, serviço ativo, capacidade, WIP, prioridades, ausências, esperas externas e rotas. Baseline: cenário aritmético transparente e política atual. | Simulação de eventos discretos/otimização com restrições, **não necessariamente ML**. Backtest de fila, throughput e P50/P90; sensibilidade a capacidade e mix. Piloto faseado com guardrails de qualidade. | Balancear equipes sem deslocar o gargalo. Não inferir serviço ativo de tempo em status; precisa captura de capacidade e trabalho. |
| **Qualidade/anomalias**: quais casos investigar? | Motivos da tabela de qualidade e regras determinísticas são baseline. Sem rótulo humano, não chamar anomalia de erro. | Ranking para revisão, depois detector apenas se gerar valor. `precision@K`, tempo até correção e projetos reincluídos; monitorar falso positivo. | Reduzir exclusões e ampliar cobertura confiável, com equipe humana no circuito. |

O [BigQuery ML pode avaliar modelos com `ML.EVALUATE`](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-evaluate),
mas isso não dispensa conjunto futuro separado, métricas por segmento nem
análise de custo. Python/scikit-learn é alternativa para experimentos com
validação temporal; a ferramenta não é a decisão principal.

### Protocolo de avaliação e ganho real

1. Fixar por escrito **decisão, instante T, população, alvo, horizonte,
   capacidade de ação e custo de erro**. Uma previsão sem ação possível não
   otimiza o processo.
2. Construir exemplos “as of T”; um projeto não pode aparecer em treino e
   teste com estados posteriores vazando para o passado. Separar meses finais
   para teste e usar janelas temporais anteriores para ajuste/validação.
3. Comparar com regra/mediana simples; reportar N, cobertura do rótulo,
   indisponíveis, erro e calibração por ambiente, status, marca/tipo e período.
   Não treinar com `estimada_migracao` como verdade observada.
4. Rodar em **modo sombra**: salvar previsão, versão e corte sem mudar prioridade
   por algumas semanas; conferir estabilidade e se alertas seriam acionáveis.
5. Fazer piloto com responsável, grupo comparável ou implantação faseada.
   Medir diferença em P50/P90 de entrega observada, espera, throughput, WIP,
   taxa de revisão por defeito (quando existir), exclusões e reclamações.
   Horas de permanência reduzidas **não são automaticamente horas de salário
   economizadas**. Não declarar causalidade por simples antes/depois.
6. Monitorar deriva das entradas, taxa de preenchimento, calibração, MAE/
   pinball/Brier conforme modelo, `precision@K`, cobertura, impacto e custo.
   Se degradar, recuar à regra baseline e revisar o contrato antes de retreinar.

Responsável atual não é atributo apropriado para prever ou justificar demora
histórica. Mesmo com atribuição histórica futura, comparar pessoas exige
complexidade, fila, dependência externa e governança; não automatizar avaliação
disciplinar. Até haver dados adequados, **BI descritivo + regras de triagem +
experimentos de processo** têm melhor relação entre valor e risco que um ML
sofisticado.
