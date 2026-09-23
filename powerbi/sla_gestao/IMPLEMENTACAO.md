# Implementação do dashboard de gestão

Estado: projeto de relatório, não PBIP conectado nem publicação Power BI. O protótipo usa dados fictícios; os recibos na página Confiança estão datados. O plano de negócio é [PLANO_DASHBOARD_ML.md](../../docs/PLANO_DASHBOARD_ML.md).

## 1. Construção em duas entregas

1. Entregar tempo por etapa, trajetória, estimativas identificadas e cobertura com os campos existentes.
2. Homologar o marco de entrega e construir o contrato de ciclos antes de liberar o KPI global ponta a ponta. “Encerrado” pode incluir resultados diferentes de orçamento entregue. Não preencher esse cartão com soma indiscriminada de etapas.

Recomendação: cinco páginas, com a primeira sendo uma onepage executiva. Não colocar detalhe, auditoria e modelos na mesma tela. Páginas: Decisão, Gargalos, Processo e equipe, Projeto, Confiança. Na primeira versão, esconder métricas futuras ou mostrar “não disponível”; jamais usar valores fictícios no relatório produtivo.

## 2. Fonte e modelo

No Power BI Desktop, Obter dados → Google BigQuery, autenticar com conta autorizada e selecionar `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`. Começar em Import; configurar atualização após a publicação diária comprovada, com margem operacional. Não armazenar credenciais no Git nem usar o nome da tabela como arquivo CSV.

Salvar como projeto PBIP quando disponível no Desktop instalado. Os arquivos `codex-model-drafts/` são propostas legíveis, não arquivos de modelo para copiar diretamente para TMDL.

| Tabela | Grão / função | Situação |
|---|---|---|
| FatoPassagens | Uma passagem, chave interval_id | Fonte existente |
| DimProjeto | Uma linha por projeto_id | Derivar sem duplicar IDs |
| DimEtapaOrigem | Etapa + ambiente, com mapeamento versionado | Validar equivalências; não unir só por nome |
| DimDataEntrada | Calendário de entrada | Relação 1:N, filtro unidirecional |
| DimDataConclusao | Calendário de conclusão | Para ciclos, não substituir data de entrada |
| FatoCiclosProposta | Um ciclo de entrega de um projeto e escopo | Ainda não implementada/homologada |

Evitar relação direta fato-fato e muitos-para-muitos por nome. Não multiplicar a contagem de projetos ao somar contagens por etapa. Transformar UTC para datas locais segundo regra documentada; não recalcular horas úteis no visual com uma aproximação diferente do pipeline.

Os ciclos precisam de início/fim comprovados, tipo de desfecho, escopo, qualidade dos endpoints, qualidade da decomposição e versão de calendário. `tempo_ciclo_observado_horas` atual é duração corrida de cadeia comprovada na origem; não é duração útil global. O diagnóstico SQL ajuda a identificar disponibilidade, não homologa o KPI.

## 3. Medidas iniciais — observadas

Exemplos DAX assumem a tabela importada renomeada `FatoPassagens`. Criar uma medida por vez. O Desktop pode exigir separadores diferentes conforme localidade. Os filtros de etapa e ambiente permanecem ativos.

```dax
Passagens KPI =
COUNT(FatoPassagens[sla_etapa_horas_uteis])

P50 Etapa h úteis =
PERCENTILEX.INC(
    FILTER(FatoPassagens, NOT ISBLANK(FatoPassagens[sla_etapa_horas_uteis])),
    FatoPassagens[sla_etapa_horas_uteis], 0.5
)

P90 Etapa h úteis =
PERCENTILEX.INC(
    FILTER(FatoPassagens, NOT ISBLANK(FatoPassagens[sla_etapa_horas_uteis])),
    FatoPassagens[sla_etapa_horas_uteis], 0.9
)

Exposição observada h úteis = SUM(FatoPassagens[sla_etapa_horas_uteis])

Passagens estimadas =
CALCULATE(COUNTROWS(FatoPassagens), FatoPassagens[origem_duracao_analise] = "estimada")

Participação estimada = DIVIDE([Passagens estimadas], COUNTROWS(FatoPassagens))
```

Zero observado válido participa; NULL não vira zero. A participação estimada acima tem todas as passagens como denominador, incluindo terminais: não chamar esse número de “taxa de erro”. Mostrar N com percentis. Percentil por passagem dá mais peso a projetos que retornam; uma análise por projeto requer outra medida e grão.

Para KPI ponta a ponta, calcular percentil **sobre uma linha por ciclo**, não sobre linhas da FatoPassagens nem sobre a soma dos percentis das etapas. A expressão final depende do contrato futuro; nenhum campo novo foi criado no BQ nesta entrega.

## 4. HTML Content: uso correto

Usar navegação, segmentações, relacionamento, filtros e drillthrough nativos do Power BI. Usar HTML Content para cartões e narrativas ou tabelas estilizadas. `prototipo.html` é referência visual independente; seu JavaScript não é uma implementação para colar no visual.

Escolher a edição aprovada pelo tenant. A edição Lite sanitiza conteúdo e tem restrições próprias; a regular não oferece automaticamente as mesmas garantias de certificação/exportação. Validar exportação PDF/PPT, acessibilidade, filtros e serviço com a edição efetivamente usada. Não carregar bibliotecas externas ou dados por scripts no HTML.

Uma medida única de HTML não cria contexto de seleção por linha. Para interações por projeto/etapa, usar o papel **Granularity** conforme a documentação do visual ou um visual nativo separado. Não desenhar botões que pareçam filtrar mas não alterem contexto.

Cartão mínimo, sem texto externo interpolado:

```dax
HTML P90 Etapa =
VAR Valor = [P90 Etapa h úteis]
VAR Texto = IF(ISBLANK(Valor), "Indisponível", FORMAT(Valor, "0.0") & " h úteis")
RETURN
"<div style='padding:20px;background:#ffffff;border:1px solid #dae3e7;border-radius:12px'>"
& "<div>P90 da etapa — observado</div><strong style='font-size:30px'>"
& Texto & "</strong><div>N = " & FORMAT([Passagens KPI], "0") & " passagens</div></div>"
```

Se interpolar nomes/observações, escapar `&`, `<`, `>`, aspas duplas e simples, nessa ordem iniciando por `&`, antes de concatenar HTML. Não inserir texto da fonte em CSS, URLs ou JavaScript. Testar labels contendo caracteres especiais. RLS é definida no modelo/serviço, nunca por esconder elementos em HTML.

## 5. Aceite antes de publicar

- Reconciliar 9.648 passagens / 2.209 projetos do recibo de 23/09 com o mesmo corte; atualizar baseline quando houver nova publicação.
- Reconciliar 6.227 durações observadas, 191 estimadas, 3.230 indisponíveis. Não congelar esses totais como regra dos próximos dias.
- Confirmar que estimativas não entram no KPI observado e que terminais não ganham duração zero.
- Abrir trajetória por projeto_id, preservando os itens de ambas as origens; o filtro de período não deve esconder silenciosamente etapas anteriores do detalhe.
- Conferir origem, população, datas, calendário, metas e denominadores em cada tooltip.
- Testar filtros cruzados, limpar seleção, nenhuma linha, um projeto, reabertura, lacuna, troca de origem, nulos e zeros.
- Ponta a ponta: amostras homologadas pelo negócio; desfechos e coortes separados; medição de cobertura sobre universo definido.
- Equipe: não usar responsável atual como executor histórico. Ranking não é produtividade ajustada por complexidade.
- ML: não liberar sem comparação temporal com baseline, análise de censura e piloto com responsável e ação definida.
- Testar no serviço permissões, atualização, custo/latência e visual HTML aprovado. Documentar dono de KPI e rotina de revisão.

## 6. Fechamento operacional

Esta entrega altera documentação, SQL somente leitura e protótipo. Não requer rebuild ou migração GCP. A agenda foi confirmada ativa às 06h Brasília. Em 24/09/2026, conferir execução automática, `orchestration_end`, publicação verificada e novo corte — não basta HTTP 200 do Scheduler. Não inferir execução futura pelo sucesso manual.

Quinta/sexta: construir e homologar dashboard com gestão. Segunda: priorizar novas tabelas de motivos, aceite, responsabilidade histórica e eventos de entrega, conforme lacunas identificadas. Nenhuma coleta nova foi implementada aqui.

## Referências

- [Modelo estrela no Power BI](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema).
- [Limitações do HTML Content](https://html-content.com/docs/limitations), [interatividade](https://html-content.com/docs/interactivity) e [sanitização](https://html-content.com/docs/sanitization).
