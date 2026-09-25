# Consultas de gestão do orçamento, indicadores e roteiro de ML — v18

Estado de referência: primeira publicação v18 verificada em 25/09/2026. Estas
consultas são **somente leitura**, em GoogleSQL, localização BigQuery `US`.
Copie **um bloco SQL por vez no editor SQL do BigQuery/DBeaver**; não cole
`SELECT` diretamente no Bash. No Cloud Shell, use `bq query` com
`--use_legacy_sql=false`, `--location=US` e limite de cobrança apropriado.
Não foram executadas no GCP nesta revisão do documento: conferir a primeira
linha, contagens e custo estimado no seu ambiente antes de divulgar resultados.
As contagens de 25/09 (7.625 passagens, 1.583 projetos, 1.685 ciclos e 4 na
fila selecionada) são um recibo datado, não metas nem números fixos.

## Como percorrer este guia

1. Conferir o grão e o corte das fontes; começar pela consulta 14 de cobertura.
2. Rodar as consultas 1–10 conforme a pergunta da área, lendo a análise de cada
   visão antes de ordenar pessoas, marcas ou etapas.
3. Usar as consultas 11–13 para explicar qualidade, evolução e trabalho aberto.
4. Escolher os indicadores e pactuar os marcos da seção **Contrato dos KPIs**.
5. Seguir o [plano detalhado de execução e avaliação de ML](PLANO_EXECUCAO_ML_V18.md)
   para preparar dados, comparar modelos e medir o benefício do piloto.

Os exemplos de interpretação abaixo são **hipotéticos**, não resultados
obtidos da base. As metas propostas são pontos de partida para aprovação
pela área. Nenhum modelo ou novo objeto de banco é criado por este guia.

### Passo a passo de uma análise reproduzível

1. Definir pergunta, unidade e população: passagem, permanência, projeto ou
   ciclo; histórico de origem, população selecionada do SLA ou backlog atual.
2. Executar uma consulta por vez no editor BigQuery, confirmar projeto e
   estimativa de bytes antes de executar. No Cloud Shell, colocar o SQL entre
   aspas simples no argumento de `bq query --use_legacy_sql=false --location=US`.
   Se o SQL contiver aspas simples, preferir arquivo `.sql` e redirecionamento
   de entrada. Não colar SQL diretamente no terminal.
3. Registrar data da execução, corte da publicação, versão da consulta,
   filtros, total da população e total com medida válida. Uma consulta não
   recupera automaticamente como a tabela estava em uma rodada passada.
4. Comparar média, mediana, P90, volume e cobertura. Inspecionar alguns casos
   acima do P90 e casos típicos, acompanhando a trajetória completa por projeto.
5. Registrar hipótese, responsável pela ação, prazo do experimento e indicador
   de sucesso. Conferir novamente com o mesmo recorte e explicitar mudança de mix.

### Qual data deve filtrar cada visão?

| Pergunta | Data/filtro correto | Efeito na interpretação |
|---|---|---|
| Uso de status no período | `entrada_status_utc`, data local São Paulo | Conta entradas na etapa; passagens iniciadas antes ficam fora. |
| Tempo de etapas terminadas no período | `saida_status_utc`, apenas duração observada | Inclui etapas longas iniciadas antes; mede encerramentos. |
| Orçamentos entregues no período | `fim_utc` dos ciclos entregues | Mede produção entregue, inclusive ciclos antigos. |
| Demanda nova no período no SLA | Primeira `inicio_utc` de `primeira_elaboracao`, por projeto | Mede Entrada reconhecida no recorte, não criação da cópia Globocorp. |
| Fila/WIP agora | Último corte válido e snapshot de cadastro | É estoque; não filtrar apenas quem entrou hoje. |
| Rankings por marca/talento/input | Coorte de início do projeto, depois enriquecer cadastro | A dimensão disponível é atual; pode ter sido corrigida depois. |

Os SQLs 1–11, salvo indicação, usam **todo o histórico disponível**. Para
filtros de datas, utilizar início inclusivo e fim exclusivo no fuso
`America/Sao_Paulo`. Aplicar o filtro no nível correto antes de agregar. Para
demanda nova, achar a primeira Entrada do projeto antes de filtrar; para
trajetória, selecionar IDs e buscar o histórico inteiro, sem truncar etapas.

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
fontes completas**. A consulta abaixo agrupa o mesmo nome de status nos dois
ambientes; antes de excluir um status do quadro, confira se o rótulo tem o mesmo
significado em ambos. Uma linha de origem é uma passagem registrada. A
`quantidade` inclui passagens abertas ou sem duração; a média, em **horas
corridas**, usa somente passagens encerradas com duração medida. Portanto, seu
denominador pode ser menor que `quantidade`. Na ViU2, a duração é candidata
histórica, não KPI homologado. Para uma comparação de tempos no recorte final
validado, use a consulta 2. Ausência de uso não prova que um status pode ser
removido sem consultar a equipe.

```sql
WITH historico AS (
  SELECT status_nome, duracao_horas AS horas_observadas
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento_viu2`
  UNION ALL
  SELECT status_nome, horas_observadas_encerradas AS horas_observadas
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento_globocorp`
)
SELECT COALESCE(NULLIF(TRIM(status_nome), ''), '(sem status)') AS status,
  COUNT(*) AS quantidade,
  ROUND(AVG(horas_observadas), 2) AS tempo_medio_horas_corridas
FROM historico
GROUP BY 1
ORDER BY quantidade DESC, status;
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

### Análise da visão 1

- **Leitura:** a primeira tabela inventaria o uso dos rótulos nas origens;
  a segunda mostra quanto desse fluxo está representado no SLA selecionado.
  `quantidade` conta entradas registradas, inclusive retornos. A média usa um
  subconjunto com saída medida; a consulta 2 explicita essa cobertura no SLA.
- **Visual:** barras de quantidade por status e tabela ao lado com tempo médio.
  Evitar um gráfico único com quantidade e horas na mesma escala.
- **Hipótese e ação:** um status raro pode ser redundante ou uma exceção
  importante. Revisar descrição e casos com o dono do processo; verificar uso
  recente por ambiente antes de propor fusão/remoção. Rótulos com escrita
  diferente continuam separados; aprovar uma equivalência antes de agrupá-los.
- **Exemplo hipotético:** 2 usos longos não justificam prioridade superior a
  800 usos moderados. Investigar volume × permanência e a função da etapa.
- **Critério de decisão:** simplificar o catálogo apenas quando a equipe
  confirmar equivalência e mantiver uma forma de distinguir a exceção nos
  dados. Guardar a vigência do rótulo para preservar a série histórica.

## 2. Média e mediana por status: candidatos a gargalo

A média utiliza durações **observadas e encerradas**. A quantidade total e a
cobertura permanecem visíveis mesmo onde não há duração calculável. Mostra todos os tipos de status,
mas compare operacional, Feedback, terceiros e Standby **separadamente**.
Entrada é espera para começar, não esforço; uma média alta não prova a causa.
Mediana abaixo é exata (`PERCENTILE_CONT`); P90 é aproximação estatística.

```sql
WITH base AS (
  SELECT projeto_id, status_nome, sla_categoria_tempo,
    sla_origem_duracao,
    IF(sla_origem_duracao = 'observada', sla_horas_corridas, NULL)
      AS horas_corridas_observadas,
    IF(sla_origem_duracao = 'observada', sla_horas_uteis, NULL)
      AS horas_uteis_observadas
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
), medidas AS (
  SELECT *,
    PERCENTILE_CONT(horas_uteis_observadas, 0.5) OVER (
      PARTITION BY sla_categoria_tempo, status_nome
    ) AS mediana_horas_uteis
  FROM base
)
SELECT sla_categoria_tempo, status_nome,
  COUNT(*) AS passagens_totais,
  COUNT(horas_uteis_observadas) AS passagens_medidas,
  ROUND(100 * SAFE_DIVIDE(COUNT(horas_uteis_observadas), COUNT(*)), 1)
    AS percentual_com_tempo_observado,
  COUNT(DISTINCT projeto_id) AS projetos,
  ROUND(SUM(horas_uteis_observadas), 2) AS exposicao_horas_uteis,
  ROUND(AVG(horas_corridas_observadas), 2) AS media_horas_corridas,
  ROUND(AVG(horas_uteis_observadas), 2) AS media_horas_uteis,
  ROUND(ANY_VALUE(mediana_horas_uteis), 2) AS mediana_horas_uteis,
  ROUND(APPROX_QUANTILES(horas_uteis_observadas, 100)[SAFE_OFFSET(90)], 2)
    AS p90_aproximado_horas_uteis
FROM medidas
GROUP BY sla_categoria_tempo, status_nome
ORDER BY exposicao_horas_uteis DESC;
```

Olhe exposição total **e** frequência: uma etapa rara e longa pode impactar
menos o fluxo que uma etapa moderada repetida muitas vezes. Não some medianas
de status para obter a mediana do ciclo.

### Análise da visão 2

1. Ordenar por exposição observada para localizar onde se concentra a
   permanência acumulada. Essa soma atravessa projetos simultâneos: não é
   quantidade de horas trabalhadas pela equipe.
2. Comparar média com mediana. Média muito acima da mediana sugere cauda longa;
   olhar P90 e os casos extremos antes de mudar o processo para todos.
3. Verificar cobertura. Uma etapa com 10% de duração medida pode parecer
   rápida justamente porque os casos mais difíceis continuam abertos ou
   sem evidência. Conferir consulta 13 e separar a incerteza.
4. Segmentar por tipo de ciclo, tipo de projeto e período; não atribuir ao
   status um aumento explicado por um mix de pedidos mais complexo.
5. Escolher um experimento: briefing mais completo, limite de WIP, rito de
   validação ou triagem de Entrada. Medir P90 e fila antes/depois, mantendo
   throughput e qualidade como condições de acompanhamento.

**Visual:** barras de P50/P90 por categoria e tabela com N/cobertura. A unidade
é passagem; uma permanência dividida na migração pode ter mais de uma linha.
Para estudar a permanência inteira, agrupar por `projeto_id` e
`sla_grupo_permanencia_id`, somar trechos e exigir evidência de todos eles.
Não somar somente os trechos conhecidos e chamá-los de permanência completa.

## 3. Tempo aguardando retorno do cliente ou de terceiros

`feedback` é espera **depois de entregar** o orçamento; `terceiros` é Retorno
Marca/Executivo **antes/durante** a elaboração. A consulta mostra ambas sem
misturá-las no mesmo indicador. O fim da passagem é uma **aproximação da
resposta**, não prova de que o cliente respondeu naquele instante; um evento
explícito de resposta resolveria essa limitação. A média inclui só esperas com saída observada;
abertas, estimadas e indisponíveis ficam expostas em colunas próprias.

```sql
WITH esperas AS (
  SELECT *,
    PERCENTILE_CONT(IF(sla_origem_duracao = 'observada',
      sla_horas_corridas, NULL), 0.5) OVER (
        PARTITION BY sla_categoria_tempo
      ) AS mediana_corridas_observadas
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  WHERE sla_categoria_tempo IN ('feedback', 'terceiros')
)
SELECT sla_categoria_tempo,
  COUNT(*) AS passagens_totais,
  COUNTIF(sla_origem_duracao = 'observada') AS esperas_observadas,
  COUNTIF(sla_origem_duracao = 'estimada_migracao') AS esperas_estimadas,
  COUNTIF(sla_origem_duracao = 'idade_aberta_no_corte') AS abertas_com_idade_calculada,
  COUNTIF(sla_origem_duracao = 'indisponivel') AS duracao_indisponivel,
  ROUND(AVG(IF(sla_origem_duracao = 'observada',
    sla_horas_corridas, NULL)), 2) AS media_horas_corridas_observadas,
  ROUND(AVG(IF(sla_origem_duracao = 'observada',
    sla_horas_uteis, NULL)), 2) AS media_horas_uteis_observadas,
  ROUND(ANY_VALUE(mediana_corridas_observadas), 2) AS mediana_horas_corridas,
  ROUND(APPROX_QUANTILES(IF(sla_origem_duracao = 'observada',
    sla_horas_corridas, NULL), 100)[SAFE_OFFSET(90)], 2) AS p90_horas_corridas
FROM esperas
GROUP BY sla_categoria_tempo
ORDER BY sla_categoria_tempo;
```

### Análise da visão 3

**Decisão:** separar uma ação de relacionamento após envio de uma ação para
obter informações necessárias à produção. Um aumento em `terceiros` pode
sugerir briefing incompleto; um aumento em `feedback` pode sugerir rito de
devolutiva pouco definido. Confirmar a hipótese com exemplos reais.

Usar horas corridas para comunicar o tempo percebido pelo cliente e horas
úteis para comparar com o calendário da operação. A coluna de idade aberta
conta apenas os casos em que foi possível calcular idade; não representa
necessariamente todas as esperas em aberto. As médias descrevem encerrados,
portanto acompanhar também o estoque atual em Aguardando Feedback no backlog.

**Visual e ação:** cartões distintos para Feedback e Terceiros com P50/P90,
seguidos de lista de casos abertos. Combinar próximo contato e responsável
comercial; testar um ritual semanal e avaliar redução do P90 sem aumento de
encerramentos administrativos usados apenas para melhorar o indicador.

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
    ) AS mediana_operacao_horas_uteis,
    PERCENTILE_CONT(TIMESTAMP_DIFF(fim_utc, inicio_utc, SECOND) / 3600.0, 0.5)
      OVER (PARTITION BY tipo_ciclo) AS mediana_janela_horas_corridas
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
  WHERE kpi_entrega_observada IS TRUE
)
SELECT tipo_ciclo,
  COUNT(*) AS entregas_observadas,
  COUNT(DISTINCT projeto_id) AS projetos,
  ROUND(AVG(janela_horas_corridas), 2) AS media_janela_horas_corridas,
  ROUND(ANY_VALUE(mediana_janela_horas_corridas), 2)
    AS mediana_janela_horas_corridas,
  ROUND(APPROX_QUANTILES(janela_horas_corridas, 100)[SAFE_OFFSET(90)], 2)
    AS p90_janela_horas_corridas,
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

### Análise da visão 4

- **Dois relógios:** janela corrida responde quanto o mercado esperou desde
  a abertura daquele ciclo; operação útil responde permanência nas etapas
  operacionais. Entrada entra no relógio operacional, embora represente fila.
- **Exemplo hipotético:** janela de 120 horas e operação de 16 horas úteis
  sugerem investigar calendário e esperas. A diferença não é calculável por
  simples subtração desses dois números porque as unidades de relógio diferem.
- **Visual:** série semanal por `fim_utc`, separando primeira elaboração e
  revisão; P50, P90, quantidade entregue e percentual de entregas com KPI
  observado. A consulta 12 fornece essa leitura temporal.
- **Ação:** definir uma meta de prazo por tipo de ciclo apenas após medir o
  baseline e o mix. Aumentar entregas enquanto cresce a idade dos abertos
  pode significar seleção de trabalhos fáceis; ler junto a consulta 13.
- **Limite:** entre `entregue` e `kpi_entrega_observada=TRUE` há diferença de
  evidência. Um envio identificado com duração estimada continua sendo um
  envio, mas sua duração não entra na promessa baseada em tempos observados.

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

### Análise da visão 5

**Uso recomendado:** reunião de revisão de carga e gargalos por etapa/área.
A linha representa uma associação entre pessoa atual, área do cadastro e
histórico de projetos. `media_horas_uteis_por_projeto` soma retornos à mesma
etapa dentro do projeto antes de tirar a média; difere da média por passagem
da consulta 2.

1. Selecionar a etapa e a área pertinente, com o mapa etapa→área confirmado
   pela operação. A consulta lista todas as áreas cadastradas e não decide
   automaticamente quem é o dono de cada status.
2. Mostrar N de projetos e composição do portfólio. Evitar comparação de
   pessoas com amostras pequenas ou complexidades distintas.
3. Abrir os projetos mais demorados; confirmar quem atuava na data, bloqueios,
   prioridade e redistribuições. A atribuição atual pode ter mudado.
4. Testar melhoria de handoff, cobertura de equipe ou limite de fila. Para
   medir carga atual, contar projetos ativos por pessoa a partir do backlog
   deduplicado; não usar toda a exposição histórica como carga de hoje.

**Marco para avançar:** a análise individual histórica depende do registro
de vigência de responsável por etapa. Até isso existir, apresentar como
“projetos associados ao cadastro atual”, com ação de revisão pela liderança.

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
  CASE WHEN COUNT(*) >= 30 THEN 'amostra_para_investigacao'
    ELSE 'amostra_pequena' END AS leitura_amostra,
  ROUND(AVG(sla_horas_corridas), 2) AS media_horas_corridas,
  ROUND(ANY_VALUE(mediana_horas_corridas), 2) AS mediana_horas_corridas,
  ROUND(APPROX_QUANTILES(sla_horas_corridas, 100)[SAFE_OFFSET(90)], 2)
    AS p90_horas_corridas,
  ROUND(AVG(sla_horas_uteis), 2) AS media_horas_uteis
FROM esperas
GROUP BY marca_atual
ORDER BY media_horas_corridas DESC, esperas_observadas DESC;
```

Para análise de negociação, repetir com `sla_categoria_tempo='terceiros'`
mostra Retorno Marca/Executivo antes da entrega, **não** a mesma espera.

### Análise da visão 6

**Visual:** dispersão de projetos/esperas × mediana de Feedback, com P90 na
tabela de detalhe. Marcas com alto volume e longa espera são candidatas a
um acordo de devolutiva; marcas com uma única passagem são casos isolados.
O corte de 30 passagens na coluna de leitura é uma regra proposta de triagem,
não garantia estatística de representatividade: várias passagens podem vir
do mesmo projeto. Para intervalos de confiança, reamostrar por projeto.

**Passos:** padronizar aliases de marca com cadastro aprovado; segmentar por
tipo de pedido e período; revisar exemplos; combinar responsável e frequência
de contato; comparar a coorte seguinte. Incluir estoque aberto na reunião,
pois o ranking de esperas encerradas pode omitir os clientes que ainda não
responderam. Não interpretar permanência no status como intenção do cliente.

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

### Análise da visão 7

O cartão da fila selecionada deve trazer **quantidade, idade mediana/P90 e
captura**; a lista prioriza os mais antigos para triagem humana. A diferença
para o backlog em Entrada exige conferir escopo, mapa e início do histórico.
Não significa que todos os itens adicionais são orçamentos esquecidos.

Um projeto só em Entrada ainda não tem entrega para medir, mas já consome
prazo de atendimento. Um retorno para Entrada depois de outras etapas pode
abrir novo ciclo e não aparecer na fila “somente Entrada”; observar também
o backlog atual e os ciclos em andamento. A consulta 13 amplia essa leitura.

**Ação:** pactuar rotina diária de triagem e motivo quando um pedido não pode
começar. **Avaliação:** acompanhar saídas da fila, idade dos remanescentes e
qualidade do briefing. Uma redução de quantidade acompanhada de aumento de
idade dos mais antigos não comprova melhoria geral. Série de estoque diária
exige registrar os cortes ao longo do tempo.

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
  ROUND(100 * SAFE_DIVIDE(COUNT(DISTINCT p.projeto_id),
    SUM(COUNT(DISTINCT p.projeto_id)) OVER ()), 1) AS percentual_dos_projetos,
  COUNT(c.ciclo_id) AS ciclos_incluindo_revisoes,
  COUNTIF(c.tipo_ciclo = 'revisao_reabertura') AS ciclos_de_revisao,
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

### Análise da visão 8

**Pergunta:** quais marcas concentram pedidos distintos e quais geram muitas
tentativas por pedido? `percentual_dos_projetos` é participação no recorte
consultado; a soma usa uma marca atual por projeto. Filtrar a coorte de
primeira Entrada antes do join de ciclos para ranking mensal de demanda.

**Visual:** Pareto de projetos por marca; tabela com projetos, revisões e
entregas. Ler junto à consulta 6: muita demanda com feedback demorado sugere
planejar relacionamento, enquanto muitas revisões pedem estudo do motivo.
Não somar rankings de meses que contam os mesmos projetos sem definir coorte.

**Ação:** acordos de briefing e calendário com marcas recorrentes. **Meta
proposta:** reduzir revisões evitáveis depois de registrar seus motivos;
quantidade de revisões por si só não mede erro, receita ou rentabilidade.

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
  ROUND(100 * SAFE_DIVIDE(COUNT(DISTINCT p.projeto_id),
    SUM(COUNT(DISTINCT p.projeto_id)) OVER ()), 1) AS percentual_dos_projetos,
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

### Análise da visão 9

**Decisão:** planejar cobertura de atendimento e validação para talentos com
demanda recorrente. Comparar Exclusivos e Interveniência separadamente antes
de atribuir diferenças ao processo; contratos e rotas podem diferir.

**Visual:** ranking por projetos únicos e participação; cruzar com marca,
tipo de input e tipo de projeto para ver concentração do portfólio. Nome é
rótulo de exibição: homônimos e grafias diferentes pedem chave de cadastro
homologada antes de relacionar com `monday_talentos_exclusivos`.

**Ação:** definir cobertura por grupo de demanda e rito de aprovação. A tabela
de talentos acrescenta vínculo e equipes atuais quando o relacionamento
estiver validado, mas não contém, por si, disponibilidade histórica ou esforço.

## 10. Tipo de entrada: de onde vêm os pedidos?

O backlog traz `tipo_input` **atual** de todos os itens capturados. Isso é o
melhor ranking disponível para canal/local do pedido, mas não é um evento
imutável de criação. Não chamar `tipo_input` de geografia se os valores do
quadro representam modalidade, iniciativa ou origem comercial.

```sql
SELECT COALESCE(NULLIF(TRIM(tipo_input), ''), '(nao informado)')
    AS tipo_input_atual,
  COUNT(DISTINCT item_id) AS itens_atuais,
  ROUND(100 * SAFE_DIVIDE(COUNT(DISTINCT item_id),
    SUM(COUNT(DISTINCT item_id)) OVER ()), 1) AS percentual_dos_itens,
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

### Análise da visão 10

**Decisão:** descobrir quais modalidades de entrada mais demandam triagem e
onde priorizar padronização de briefing. Primeiro conferir os valores reais
de `tipo_input` com a área; “local do pedido” pode exigir outro campo.

**Visual:** participação por tipo e quantidade não informada. Comparar
backlog atual e SLA em painéis distintos, explicando seus denominadores.
Uma concentração no snapshot atual não prova maior chegada recente, porque
pedidos antigos que continuam no quadro também são contados.

**Ação:** criar checklist adequado ao canal; cruzar com P90 de primeira
elaboração por projeto para localizar hipóteses. Para concluir que um canal
causa demora, avaliar complexidade e seleção de pedidos. **Marco:** origem
do pedido preenchida na Entrada e preservada mesmo após correções posteriores.

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

### Análise da visão 11

Na qualidade, contar projetos únicos por motivo e priorizar os que bloqueiam
uma decisão importante. Um projeto pode aparecer em vários motivos e também
ter trechos aproveitáveis no SLA. Acompanhar resolução por ID entre rodadas:
queda no total pode vir de mudança de escopo, não necessariamente de correção.

Na coorte de ciclos, revisões são novas tentativas do mesmo projeto. Um mês
recente terá naturalmente mais ciclos abertos. Para estimar probabilidade de
entrega, comparar coortes com a mesma janela de acompanhamento ou usar análise
de sobrevivência; não comparar a razão entregue/total de setembro recém-aberto
com janeiro já maturado.

## 12. Evolução semanal: entregas, prazo e cobertura

Usa as 12 semanas completas anteriores à semana do último corte. Semana começa
na segunda-feira, em São Paulo. A data é a **entrega**, e `entregas_totais`
inclui envios identificados mesmo quando seu tempo não sustenta o KPI observado.
Uma semana ausente do resultado não comprova zero demanda; conferir cobertura
histórica antes de preencher lacunas de calendário com zero.

```sql
WITH ciclos AS (
  SELECT * FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
), referencia AS (
  SELECT DATE_TRUNC(DATE(MAX(corte_utc), 'America/Sao_Paulo'), WEEK(MONDAY))
    AS fim_exclusivo
  FROM ciclos
), entregas AS (
  SELECT c.*,
    DATE_TRUNC(DATE(fim_utc, 'America/Sao_Paulo'), WEEK(MONDAY)) AS semana,
    IF(kpi_entrega_observada, operacao_horas_uteis, NULL) AS horas_kpi,
    IF(kpi_entrega_observada,
      TIMESTAMP_DIFF(fim_utc, inicio_utc, SECOND) / 3600.0, NULL) AS janela_kpi
  FROM ciclos c CROSS JOIN referencia r
  WHERE situacao = 'entregue'
    AND DATE(fim_utc, 'America/Sao_Paulo') >= DATE_SUB(r.fim_exclusivo, INTERVAL 12 WEEK)
    AND DATE(fim_utc, 'America/Sao_Paulo') < r.fim_exclusivo
), medidas AS (
  SELECT *, PERCENTILE_CONT(horas_kpi, 0.5) OVER (
    PARTITION BY semana, tipo_ciclo
  ) AS mediana_operacao
  FROM entregas
)
SELECT semana, tipo_ciclo,
  COUNT(*) AS entregas_totais,
  COUNT(DISTINCT projeto_id) AS projetos_entregues,
  COUNT(horas_kpi) AS entregas_com_tempo_observado,
  ROUND(100 * SAFE_DIVIDE(COUNT(horas_kpi), COUNT(*)), 1) AS cobertura_percentual,
  ROUND(ANY_VALUE(mediana_operacao), 2) AS mediana_operacao_horas_uteis,
  ROUND(APPROX_QUANTILES(horas_kpi, 100)[SAFE_OFFSET(90)], 2)
    AS p90_operacao_horas_uteis,
  ROUND(AVG(janela_kpi), 2) AS media_janela_horas_corridas
FROM medidas
GROUP BY semana, tipo_ciclo
ORDER BY semana, tipo_ciclo;
```

**Análise:** plotar entregas e P90 em gráficos alinhados no tempo, sempre com
cobertura e N. Uma queda de P90 junto com queda forte da cobertura pede
investigação antes de comemorar. Ler o mix de primeiras elaborações/revisões
separadamente e marcar a data de uma mudança de processo no gráfico. Para
estimar ganho, comparar períodos equivalentes e incluir idade dos abertos.

## 13. Ciclos em andamento: o que precisa de acompanhamento?

A idade abaixo é corrida entre o início do ciclo e o corte publicado. A
última etapa representa o histórico **no corte**; o cadastro do board pode
estar mais recente. NULL na idade da etapa significa evidência insuficiente
para afirmá-la, não espera zero. A ordenação é uma fila de investigação.

```sql
WITH ultima_etapa AS (
  SELECT projeto_id, ciclo_id, status_nome, ambiente_origem,
    sla_categoria_tempo, sla_origem_duracao, sla_horas_uteis
  FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
  WHERE ciclo_id IS NOT NULL
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY projeto_id, ciclo_id
    ORDER BY entrada_status_utc DESC, ordem_etapa DESC, interval_id DESC
  ) = 1
)
SELECT c.projeto_id, c.ciclo_id, c.tipo_ciclo,
  c.inicio_utc, c.corte_utc,
  ROUND(TIMESTAMP_DIFF(c.corte_utc, c.inicio_utc, SECOND) / 3600.0, 2)
    AS idade_ciclo_horas_corridas,
  u.status_nome AS ultima_etapa_no_corte,
  u.ambiente_origem, u.sla_categoria_tempo, u.sla_origem_duracao,
  IF(u.sla_origem_duracao = 'idade_aberta_no_corte', u.sla_horas_uteis, NULL)
    AS idade_etapa_horas_uteis_com_evidencia,
  c.contem_estimativa, c.duracao_completa
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento` c
LEFT JOIN ultima_etapa u USING(projeto_id, ciclo_id)
WHERE c.situacao = 'em_andamento'
ORDER BY idade_ciclo_horas_corridas DESC, c.projeto_id;
```

**Análise:** revisar primeiro os ciclos antigos e os que estão sem evidência
de duração. Identificar bloqueio, próximo passo e dono. Se o último estado do
board divergir do corte, aguardar/validar a atualização antes de cobrar uma
ação já concluída. O ciclo entregue em Feedback não está “em andamento” nesta
tabela, embora o relacionamento com cliente continue; a espera de Feedback
é acompanhada pela consulta 3 e pelo status atual do backlog.

## 14. Confiança do painel: cobertura, chaves e corte

O universo reconciliado desta consulta é a união de projetos do SLA e da
qualidade. Itens sem mapa ou fora do escopo antes dessa seleção não aparecem
nesse denominador. O backlog total é outra população. A consulta é diagnóstica;
não substitui os [testes completos v18](VALIDACAO_E_ANALISE_CICLOS_V18.md).

```sql
WITH s AS (
  SELECT * FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
), c AS (
  SELECT * FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`
), q AS (
  SELECT * FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_baixa_qualidade_de_dado`
), universo AS (
  SELECT projeto_id FROM s
  UNION DISTINCT
  SELECT projeto_id FROM q
)
SELECT
  (SELECT COUNT(*) FROM universo) AS projetos_universo_reconciliado,
  (SELECT COUNT(DISTINCT projeto_id) FROM s) AS projetos_no_sla,
  (SELECT COUNT(DISTINCT projeto_id) FROM q) AS projetos_com_diagnostico,
  (SELECT COUNT(DISTINCT q.projeto_id) FROM q
    WHERE NOT EXISTS (SELECT 1 FROM s WHERE s.projeto_id = q.projeto_id))
    AS projetos_diagnostico_fora_sla,
  (SELECT COUNT(*) - COUNT(DISTINCT interval_id) FROM s)
    AS chaves_passagem_repetidas_ou_nulas,
  (SELECT COUNT(*) - COUNT(DISTINCT ciclo_id) FROM c)
    AS chaves_ciclo_repetidas_ou_nulas,
  (SELECT COUNTIF(situacao = 'entregue') FROM c) AS ciclos_entregues,
  (SELECT COUNTIF(kpi_entrega_observada) FROM c) AS entregas_kpi_observado,
  (SELECT ROUND(100 * SAFE_DIVIDE(COUNTIF(kpi_entrega_observada),
    COUNTIF(situacao = 'entregue')), 1) FROM c) AS cobertura_tempos_das_entregas_pct,
  (SELECT COUNT(DISTINCT corte_utc) FROM c) AS quantidade_cortes_ciclos,
  (SELECT MIN(corte_utc) FROM c) AS menor_corte_ciclos,
  (SELECT MAX(corte_utc) FROM c) AS maior_corte_ciclos,
  (SELECT MAX(cadastro_atual_capturado_em) FROM s) AS captura_cadastro_sla;
```

**Análise:** duplicidade/nulidade de chave deve ser zero e a publicação de
ciclos deve usar um único corte. Divergência pede investigação antes de juntar
as tabelas. Cobertura do tempo das entregas mede quais envios sustentam cálculo
completo observado; não é percentual de todos os projetos do Monday cobertos.
Registrar essa cobertura junto aos KPIs e conferir se ela mudou entre rodadas.

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

## Contrato dos KPIs: como calcular, agir e estabelecer metas

Cada indicador deve ter uma ficha com: código, pergunta, dono do processo,
fórmula, fonte, grão, filtro, data de referência, unidade, frequência, baseline,
meta, exclusões, versão e ação quando sair da faixa. Os donos abaixo são
**papéis sugeridos**, a confirmar na operação.

| KPI / pergunta | Fórmula, população e consulta | Frequência / dono sugerido | Meta inicial proposta e ação |
|---|---|---|---|
| K01 — Prazo percebido de entrega | P50/P90 de `(fim_utc-inicio_utc)` em horas corridas, por tipo de ciclo com KPI observado; Q4/Q12. | Semanal / liderança de Orçamento. | Reduzir P90 em 10% após 8 semanas de piloto, com mix comparável e cobertura estável. Rever esperas/rotas. |
| K02 — Permanência operacional | P50/P90 de `operacao_horas_uteis`, primeira elaboração e revisão separadas; Q4. | Semanal / liderança de Orçamento. | Escolher uma etapa-alvo e testar redução de 10% de seu P90; verificar se prazo total também melhora. |
| K03 — Volume entregue | Contagem de ciclos `situacao='entregue'` por semana de `fim_utc`, mais projetos únicos; Q12. | Semanal / gestão do fluxo. | Não cair mais de 5% no piloto por efeito da intervenção, considerando demanda/mix; é condição de acompanhamento, não quota individual. |
| K04 — Espera de Feedback | P50/P90 de passagens `feedback` com duração observada; Q3/Q6. | Semanal / relacionamento comercial. | Reduzir P90 em 10% no grupo-piloto em 8 semanas; acompanhar abertos e confirmar marco de resposta. |
| K05 — Espera por informações | P50/P90 de `terceiros` observado; Q3. | Semanal / responsável pelo briefing. | Diminuir tempo de espera após implantação do checklist; prazo/meta final depende do baseline por tipo de pedido. |
| K06 — Fila de Entrada | Projetos na fila selecionada, idade P50/P90 e lista antiga; Q7. | Diário / triagem. | Revisar 100% dos casos selecionados na rotina diária; reduzir P90 da idade em 15% no piloto, sem ocultar itens fora do escopo. |
| K07 — Trabalho em andamento | Ciclos `em_andamento` e idade no corte; Q13. | Diário / coordenação. | Definir limite de WIP após medir capacidade; inicialmente todo ciclo antigo revisado tem próximo passo/dono. |
| K08 — Intensidade de revisão | Ciclos `revisao_reabertura` / projetos da mesma coorte, com janela de acompanhamento comum; Q11. | Mensal / qualidade do processo. | Baseline primeiro. Redução desejável apenas de revisão classificada como evitável; não eliminar revisões comerciais legítimas. |
| K09 — Concentração da demanda | Projetos por marca/talento/input / total de projetos do mesmo recorte; Q8–Q10. | Mensal / planejamento. | Sem meta de “menor concentração” automática. Usar top grupos para pactuar cobertura e calendário. |
| K10 — Cobertura dos tempos de entrega | Ciclos com KPI observado / ciclos entregues; Q14. | Diário, revisão semanal / dados. | Manter variação dentro de 2 pontos percentuais no piloto ou explicar/recalcular comparação. Aumentar cobertura apenas com evidência corrigida. |
| K11 — Integridade e atualização | Duplicidade de chave, órfãos, cortes, publicação e captura; Q14 + validações v18. | Diário / engenharia de dados. | Zero chaves inválidas/órfãs; publicação diária verificada. Prazo operacional sugerido: resultado disponível até 07h São Paulo, a pactuar. |
| K12 — Correção efetiva | Projetos com problema confirmado que foram corrigidos / projetos confirmados acompanhados; tempo até correção. | Semanal / dados + operação. | Prazo de resolução proposto de 5 dias úteis para problemas priorizados; exige histórico de triagem, que não está na tabela atual. |

“SLA” hoje representa medidas do processo. O indicador **percentual entregue
no prazo combinado** só pode ser desenvolvido quando `prazo_pactuado` existir
com vigência e regras de pausa. Sua fórmula futura será entregas dentro do
prazo / entregas com prazo válido; divulgar também a cobertura desse cadastro.
Não substituir prazo combinado pela média histórica nem pelo P90 sem acordo.

### Como construir o baseline e aprovar a meta

1. Escolher, como proposta inicial, 8 semanas completas com contrato comparável.
   Separar por tipo de ciclo e processo atual; não usar migração estimada como
   duração observada. Se o fluxo atual ainda não tem histórico suficiente,
   começar uma coleta prospectiva e usar o histórico apenas como referência.
2. Registrar N de projetos/ciclos, cobertura, distribuição de durações e mix.
   Para grupos com menos de 30 projetos, sinalizar amostra pequena e priorizar
   descrição de casos. Esse número é uma convenção de leitura proposta;
   precisão estatística depende da dispersão, não só de N.
3. Fixar baseline B e fórmula antes do piloto. Para P90, melhoria relativa =
   `100 × (B - P90_piloto) / B`; se B=0, usar diferença absoluta. Para cobertura,
   usar diferença em pontos percentuais. Exemplo hipotético: 80→72 horas é
   redução de 10%; 70%→72% de cobertura é aumento de 2 pontos percentuais.
4. Aprovar meta com capacidade e ação concreta. Exemplo de ficha: “reduzir P90
   da primeira elaboração em 10% com revisão de briefing, em 8 semanas,
   sem queda de cobertura >2 p.p. e sem piora relevante da idade dos abertos”.
5. Comparar semanas e grupos semelhantes. Para quantificar incerteza,
   reamostrar projetos inteiros (bootstrap), preservando seus ciclos; não
   tratar cada passagem do mesmo projeto como amostra independente.
6. Analisar condição de acompanhamento e causas de mudança. Se a cobertura
   mudou, o volume foi atípico ou a equipe mudou, registrar e não atribuir
   automaticamente o ganho à intervenção.

### Marcos de entrega e aceite

As semanas abaixo começam no **D0 de aprovação do plano**, não são datas de
implantação já cumpridas. Falta de rótulo ou evidência estende o marco; uma
semana de calendário não aprova um modelo por si só.

| Marco | Janela proposta | Entrega concreta | Critério para avançar |
|---|---|---|---|
| M0 — Definições | Semana 1 | Dicionário de status, grão, relógios, dono e fichas K01–K11. | Área confirma significado e filtros; divergências registradas. |
| M1 — Consultas homologadas | Semanas 1–2 | Execução BigQuery com custo/contagens e casos rastreados. | Sem erro de chave/join; totais reconciliados; amostra de trajetórias aprovada. |
| M2 — Baseline e painel | Semanas 2–3 | Painel com volume, P50/P90, fila e cobertura; relatório de baseline. | Todo cartão tem corte, população e N; meta aprovada com responsável. |
| M3 — Piloto de processo | 8 semanas após M2 | Checklist/rito/triagem escolhido e registro das intervenções. | Evidência de execução e comparação de mix; avaliação do resultado e condições. |
| M4 — Dados para previsão | Em paralelo, após M1 | Exemplos com dados conhecidos em T, alvo e período de disponibilidade. | Sem uso de atributos futuros; rótulos e censura auditados; cortes temporais congelados. |
| M5 — Modelo candidato | Após M4 | Baseline e modelo comparados em teste futuro intocado. | Ganho sobre baseline, incerteza/segmentos avaliados e critério do modelo atendido. |
| M6 — Sombra e piloto assistido | 2–4 semanas de sombra, depois piloto | Previsões registradas e revisadas, sem prioridade automática inicialmente. | Volume suficiente de desfechos; precisão útil à operação; retorno à regra simples definido. |

### Ritual para transformar indicador em melhoria

- **Diário, 15 minutos:** conferir publicação, fila antiga e ciclos abertos;
  registrar próximo passo, dono e motivo do bloqueio.
- **Semanal, 45 minutos:** escolher um gargalo com dados e casos; acompanhar
  experimento anterior; evitar iniciar muitas intervenções simultâneas.
- **Mensal:** rever mix de demanda, metas, rotas e capacidade; revisar dicionário
  e campos ausentes que impedem decisões.
- **Fim do piloto:** manter, ajustar ou interromper a mudança com base em
  efeito, incerteza, esforço de manutenção e qualidade. Previsão só tem valor
  quando a ação tomada a partir dela melhora o resultado.

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

O [plano de execução de ML](PLANO_EXECUCAO_ML_V18.md) detalha os dados por
campo, preparação, marcos, treino, teste temporal, métricas, metas propostas,
piloto e manutenção de cada caso abaixo. A tabela é o mapa de escolha.

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
| **Faixa de prazo na entrada**: que intervalo prometer? | Alvo comercial: janela corrida até Feedback observado. Alvo operacional separado: horas úteis de operação. Features conhecidas na Entrada (tipo, complexidade, marca agrupada, calendário), nunca status final ou cadastro corrigido depois. Baseline: P50/P90 por segmento com fallback global. | Regressão quantílica/gradient boosting apenas se superar baseline. MAE para P50, pinball loss P50/P90, cobertura do P90 perto de 90%, por período/segmento. | Melhor promessa e menos cobrança. Horas úteis operacionais não são uma data de entrega; abertos exigem análise de censura. Precisa snapshot da Entrada e amostra suficiente no fluxo atual. |
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
