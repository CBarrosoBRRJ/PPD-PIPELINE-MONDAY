# Primeira página do Power BI: gestão das etapas observadas

Este roteiro é executável no Power BI Desktop depois de conectar a tabela
`gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento` por Import.
Não foi conectado ou executado nesta máquina; as medidas abaixo são rascunhos
para validar no Desktop. O [recibo de 24/09](../../docs/ESTADO_GCP_2026_09_24.md)
é a referência de contagem inicial.

## 1. Preparar a tabela

Renomeie a consulta importada para `FatoPassagens`. Confira antes de criar visuais:

| Campo | Tipo esperado | Uso |
|---|---|---|
| `interval_id`, `projeto_id`, `ambiente_origem`, `status_nome` | Texto | Grão, projeto e filtros |
| `sla_etapa_horas_uteis` | Número decimal | Somente KPI observado por passagem |
| `origem_duracao_analise`, `classificacao_consumo` | Texto | Proveniência e auditoria |
| `saida_status_local` | Data/hora | Semana da saída observada |
| `corte_globocorp_utc` | Data/hora UTC | Data de atualização dos dados |

`interval_id` deve ser único; `projeto_id` pode se repetir. Não agregar duração
estimada à coluna do KPI. Para uma primeira montagem, use diretamente a tabela
de passagens. A dimensão de calendário vem em seguida, após definir o período
e a regra de fuso no modelo. Não crie relacionamento por nome do projeto.

## 2. Medidas para criar em “Nova medida”

Cada bloco é **uma** medida. Use exatamente os nomes abaixo para que o cartão
HTML funcione. Dependendo da localidade do Desktop, ajuste separadores `,` para
`;` no editor DAX. O projeto de modelagem também registra essas definições em
`codex-model-drafts/measure-drafts.json`.

```dax
PassagensKPIEtapa =
COUNT(FatoPassagens[sla_etapa_horas_uteis])
```

```dax
ProjetosKPIEtapa =
CALCULATE(
    DISTINCTCOUNT(FatoPassagens[projeto_id]),
    NOT ISBLANK(FatoPassagens[sla_etapa_horas_uteis])
)
```

```dax
P50EtapaHorasUteis =
PERCENTILEX.INC(
    FILTER(FatoPassagens, NOT ISBLANK(FatoPassagens[sla_etapa_horas_uteis])),
    FatoPassagens[sla_etapa_horas_uteis], 0.5
)
```

```dax
P90EtapaHorasUteis =
PERCENTILEX.INC(
    FILTER(FatoPassagens, NOT ISBLANK(FatoPassagens[sla_etapa_horas_uteis])),
    FatoPassagens[sla_etapa_horas_uteis], 0.9
)
```

```dax
ExposicaoObservadaHorasUteis =
SUM(FatoPassagens[sla_etapa_horas_uteis])
```

```dax
ParticipacaoEtapaExposicao =
DIVIDE(
    [ExposicaoObservadaHorasUteis],
    CALCULATE(
        [ExposicaoObservadaHorasUteis],
        REMOVEFILTERS(FatoPassagens[status_nome])
    )
)
```

```dax
CorteDado = MAX(FatoPassagens[corte_globocorp_utc])
```

Formate P50/P90 com uma casa decimal, participação como percentual e o corte
como data/hora **identificada UTC**. Não some `ProjetosKPIEtapa` entre status:
o mesmo projeto pode ter muitas passagens. O denominador de participação tira
apenas o filtro de status; mantém ambiente e período. Se no futuro o status vier
de `DimEtapaOrigem`, ajuste a expressão para remover esse filtro da dimensão.

## 3. Montagem da página

Título: **Onde o tempo observado se concentra?** Subtítulo permanente:
“Passagens elegíveis com saída observada; população selecionada; horas úteis.”

| Posição | Visual nativo / HTML Content | Campos e regra |
|---|---|---|
| Topo esquerdo | Segmentadores nativos | `ambiente_origem`, `status_nome`, período de `saida_status_local` |
| Topo direito | Cartão nativo | `[CorteDado]` e aviso de dados não atualizados se corte antigo |
| Primeira faixa | Quatro cartões HTML | N observado, P50, P90, exposição; selecionar **uma** origem e etapa |
| Centro esquerdo | Barras horizontais nativas | Eixo `status_nome`, valor `[ExposicaoObservadaHorasUteis]`; segmentar origem |
| Centro direito | Matriz nativa | Origem → status; N, projetos, P50, P90, exposição e participação |
| Rodapé | Linha semanal nativa | Semana da saída local, `[P90EtapaHorasUteis]`; mostrar N no tooltip |

Não usar a data da publicação como eixo da tendência. Na primeira iteração,
adicione `saida_status_local` ao visual e escolha semana; confira se o Desktop
está agregando pela semana local esperada. Para reconciliação independente,
execute [`dashboard_tendencia_etapas.sql`](../../tabelas/monday_sla_orcamento/sql/dashboard_tendencia_etapas.sql).
Os percentis da query são aproximados; DAX calcula sobre as passagens filtradas.

## 4. Cartões no HTML Content

Adicione um visual HTML Content e coloque a medida abaixo no papel de conteúdo
HTML. Use filtros nativos da página; o HTML não contém JavaScript. Este cartão
evita comparar duas origens ou vários status sem contexto. Os textos interpolados
são apenas números formatados por DAX, sem campos livres do Monday.

```dax
HTMLResumoEtapa =
VAR UmaOrigem = HASONEVALUE(FatoPassagens[ambiente_origem])
VAR UmaEtapa = HASONEVALUE(FatoPassagens[status_nome])
VAR N = COALESCE([PassagensKPIEtapa], 0)
VAR P50 = IF(N > 0, FORMAT([P50EtapaHorasUteis], "0.0"), "—")
VAR P90 = IF(N > 0, FORMAT([P90EtapaHorasUteis], "0.0"), "—")
VAR Horas = IF(N > 0, FORMAT([ExposicaoObservadaHorasUteis], "#,0.0"), "—")
RETURN
IF(
    N = 0,
    "<div style='padding:16px;border:1px solid #dae3e7;border-radius:10px'>Sem passagens observadas no contexto selecionado.</div>",
    IF(
    NOT (UmaOrigem && UmaEtapa),
    "<div style='padding:16px;border:1px solid #dae3e7;border-radius:10px'>Selecione uma origem e uma etapa para ver os indicadores observados.</div>",
    "<div style='display:flex;flex-wrap:wrap;gap:12px'>"
        & "<div style='flex:1;min-width:160px;padding:16px;background:#eef7f7'><div>Passagens</div><strong style='font-size:28px'>" & FORMAT(N, "#,0") & "</strong></div>"
        & "<div style='flex:1;min-width:160px;padding:16px;background:#eef7f7'><div>P50 • h úteis</div><strong style='font-size:28px'>" & P50 & "</strong></div>"
        & "<div style='flex:1;min-width:160px;padding:16px;background:#eef7f7'><div>P90 • h úteis</div><strong style='font-size:28px'>" & P90 & "</strong></div>"
        & "<div style='flex:1;min-width:160px;padding:16px;background:#eef7f7'><div>Exposição • h úteis</div><strong style='font-size:28px'>" & Horas & "</strong></div>"
        & "</div>"
    )
)
```

Confirme com a edição do HTML Content aprovada no ambiente que as propriedades
CSS são aceitas. Se o visual não renderizar ou não for autorizado, use cartões
nativos com as mesmas medidas; o modelo e as definições permanecem válidos.
O visual HTML de medida única não fornece seleção por linha da matriz: clique
na matriz ou nas barras nativas para filtrar os cartões.

## 5. Testes de aceite na página

1. Sem filtro de origem/etapa, o HTML pede seleção; com uma seleção, mostra quatro números.
2. Um filtro sem passagens elegíveis mostra a mensagem de ausência de dados,
   sem inventar duração.
3. No corte de 24/09, sem filtros, `[PassagensKPIEtapa]` deve ser 6.227;
   `COUNTROWS(FatoPassagens)` deve ser 9.672 e projetos distintos 2.209.
4. Compare uma origem e etapa com a query de tendência e com
   [`dashboard_etapas.sql`](../../tabelas/monday_sla_orcamento/sql/dashboard_etapas.sql).
5. Teste uma etapa com retorno, um projeto com itens nas duas origens, e clique
   “Limpar seleções”. Confira que N, P50, P90 e barras respondem aos mesmos filtros.
6. A participação da exposição das etapas de uma origem/período deve somar
   aproximadamente 100% quando a lista de status for completa. Se houver
   filtros adicionais de status, revise o denominador.
7. Confira no serviço a atualização, os filtros, a exportação permitida e a
   apresentação de tela estreita. Não publicar cartão global de entrega nesta fase.

Depois de salvar um PBIP real no Desktop, poderemos revisar TMDL e interações
do relatório no projeto. O protótipo `prototipo.html` representa a visão futura
e usa números fictícios; estes cartões são a primeira versão ligada à fonte real.
