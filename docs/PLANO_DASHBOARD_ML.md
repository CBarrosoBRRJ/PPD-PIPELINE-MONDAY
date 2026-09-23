# Plano de consumo: dashboard e pesquisa de ML

Data: 23/09/2026. Proposta, não dashboard/modelo já implantado.
Fonte: contrato executável v7, código, testes e resultados BQ fornecidos pelo operador.
Não houve nova leitura ao vivo do BQ nesta revisão: sessão local sem permissão
para listar execuções Cloud Run. Nenhuma tabela/modelo/serviço novo criado.

## 1. Base e limites

Tabela: gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento.
Uma linha por passagem; interval_id é a chave. Projeto: projeto_id; item_id muda
entre contas. Recibo: 9.648 passagens / 2.209 projetos, 6.227 passagens com KPI
observado, 191 estimadas, 3.230 sem duração analítica. Ausência de duração inclui
terminais legítimos: não classificar todas essas linhas como erro.
Nas passagens elegíveis, 6.202 eram ViU2 e apenas 25 Globocorp no corte conferido.
Não comparar ambientes como experimento de produtividade nem treinar modelo
Globocorp robusto com essa amostra. Escopo selecionado/mapeado, não toda a operação.

KPI observado: sla_etapa_horas_uteis. Análise com hipóteses:
duracao_analise_horas e duracao_analise_horas_uteis; mostrar origem_duracao_analise.
Não somar toda a trajetória como SLA integral entre ambientes. Não substituir
NULL por zero. Horas úteis são permanência em expediente, não esforço trabalhado.
Última etapa observada não comprova status atual, abandono ou fila ativa.
Cadastros atuais de marca/talento/responsável não são necessariamente atributos
historicamente disponíveis no começo da passagem.

## 2. Dashboard inicial (quinta 24 e sexta 25/09)

Nome sugerido: Permanência por etapa e qualidade do fluxo de orçamento.
Cada visual deve mostrar origem, período, denominador e corte da publicação.
Página padrão somente observadas; página/camada separada para análise estimada.

| Indicador | Como calcular | Decisão/limitação |
|---|---|---|
| Tempo típico e cauda | Mediana, P75 e P90 de sla_etapa_horas_uteis por ambiente/status | Onde a permanência é maior; sempre mostrar N |
| Tempo médio | AVG(sla_etapa_horas_uteis) | Complementa, não substitui mediana/P90 |
| Passagens medidas | COUNT(sla_etapa_horas_uteis) | Denominador da duração; zero válido conta |
| Projetos medidos | DISTINCTCOUNT projeto_id nas linhas com KPI não nulo | Não somar os distintos de cada status |
| Volume de saídas | Contagem de passagens elegíveis por data de saída | Saídas de etapas, não projetos entregues |
| Evolução semanal | Mediana/P90 por semana de saída, ambiente/status | Comparar períodos completos e mesma população |
| Composição da evidência | Contagem/% por classificacao_consumo e origem_duracao_analise | Explicita elegíveis, terminais e lacunas |
| Participação estimada | COUNTIF(origem=estimada)/COUNT(duracao_analise_horas_uteis) | Aproximadamente 3% das durações do recibo; não de todos os projetos |
| Sensibilidade da estimativa | Métricas observadas versus métricas unificadas no mesmo recorte | Mostra impacto da hipótese, não dois indicadores equivalentes |
| Distribuição do tempo por etapa | Soma das horas observadas por etapa / soma observada do recorte | Exposição acumulada; não tempo total do processo nem capacidade |
| Qualidade das trajetórias | Uma linha por projeto com eh_ultima_etapa_observada | qualidade_trajetoria não homologa completude vitalícia |
| Retornos/reaberturas | Projetos distintos com retorno_observado_origem/reabertura_comprovada_origem | Evento observado na origem; não chamar automaticamente de retrabalho |
| Linha do tempo | projeto_id, ordem_etapa, datas, duração e origem | Estimativas em estilo distinto, lacunas explícitas |

Não entregar ainda: percentual dentro de SLA (não há metas pactuadas), receita,
conversão comercial, fila atual, previsão de encerramento global, ranking individual
de produtividade ou soma vitalícia. Esses usos exigem dados/contratos adicionais.
Mesmo encerramentos observados não significam venda; separar Encerrado/Declinados.

### Páginas e modelo semântico

1. Visão executiva: projetos/passagens medidos, mediana/P90 por etapa, cobertura,
   corte da fonte e data de atualização do relatório. Sem cartão de SLA total.
2. Diagnóstico: distribuição de tempos e tendência, ambiente separado,
   marca/talento apenas quando identidade normalizada e cobertura conferidas.
3. Projeto: pesquisa por projeto_id ou item_id_globocorp e trajetória completa
   observada. Filtro de data do painel não deve esconder o restante da trajetória
   sem um aviso claro.
4. Qualidade/estimativas: motivo de exclusão do KPI, participação estimada e
   comparação entre duração observada e unificada.

Preferência: Power BI, se já licenciado na organização, conector nativo BigQuery
em Import para este volume pequeno e atualização diária. DirectQuery não é
necessário para poucos milhares de linhas. Alternativa: Looker Studio, se for
a ferramenta já aprovada, sem comprar plataforma antes de avaliar licenças.

Fato Passagens; dimensões de Projeto, Ambiente/Status e Calendário no modelo BI.
Status deve ter chave com ambiente e código/rótulo, sem unir códigos entre contas.
Calendários com papéis distintos de entrada/saída; data de saída como padrão
das métricas de passagens concluídas. Trajetória usa todo o projeto.
Relações 1:N, filtro unidirecional, sem joins por nome de projeto.
Ocultar colunas de linhagem volumosas no modelo destinado ao usuário.
Não criar novas tabelas BQ só para montar o painel nesta etapa.
Atualizar o relatório depois da publicação confirmada, não presumir sucesso
só porque passou das 6h. Permissões de leitura e público autorizados pela área.

Horário útil existente: seg-sex 10–13/14–19 São Paulo, feriados BR PUBLIC + extras.
Reutilizar cálculo do pipeline; não refazer DAX ignorando almoço/feriados.
Medidas: média = AVERAGE; mediana = MEDIAN; percentil = PERCENTILEX.INC sobre
linhas cujo KPI não seja BLANK. Nulos fora da amostra; zero útil dentro.
Sempre mostrar N; sugerir aviso N<30, sem tratar 30 como garantia estatística.
Consulta SQL inicial: tabelas/monday_sla_orcamento/sql/dashboard_etapas.sql.

### Aceite do dashboard

Conferir totais com BQ no mesmo corte; validar amostra de projetos incluindo
ABRALE, retornos, terminal, zero útil e lacuna. Aplicar filtros e conferir distintos.
Conferir que as 191 estimativas não entram no KPI observado e que o total de
projetos não é a soma dos cartões de status. Reconciliar os recortes temporais.
Medianas de grupos não devem ser somadas nem médias agregadas sem pesos.

## 3. ML: pesquisa prioritária, não aprovação para produção

Não existe melhor modelo demonstrado antes do teste. A tabela permite estudo
exploratório; a validade do alvo, atributos no instante certo e cobertura futura
precisam ser comprovadas. Não usar estimativas v6/v7 como verdade de treinamento.

| Caso | Primeira abordagem | Avaliação | Dependência |
|---|---|---|---|
| Tempo típico/P90 para uma nova passagem | Baseline mediana/P90 etapa-origem, depois GradientBoostingRegressor com perda quantílica | MAE em horas, pinball loss, cobertura do P90 e erro por etapa | Somente fechadas observadas; viés de seleção das concluídas explícito |
| Chance de sair da etapa em H horas úteis | Kaplan-Meier por etapa e Cox; comparar Random Survival Forest | C-index IPCW, Brier e calibração nos horizontes | Censura confiável: NULL histórico não é automaticamente caso ativo |
| Risco de superar referência | Regressão logística regularizada, depois árvores | PR-AUC, precision@K, recall e calibração | Meta pactuada ou limiar histórico calculado só no treino; não chamar atraso contratual sem meta |
| Casos atípicos para revisão | P90/IQR por etapa antes de Isolation Forest | Proporção de alertas úteis revisados pela equipe | Não é prova de erro/fraude ou avaliação individual |
| Previsão de volume/capacidade | Baseline sazonal antes de modelo temporal | MAE/MASE e backtest por semana | Histórico contínuo da população atual, não só amostra mapeada |

Prioridade sugerida: baseline de permanência + pesquisa de quantis; posteriormente
modelo de sobrevivência quando o estado atual/censura estiverem confiáveis.
Não começar por deep learning/LLM: pouca amostra atual, forte mudança de ambiente,
e informação histórica incompleta. IA generativa pode narrar medidas conferidas,
mas não deve calcular SLA, inventar causa ou prever prazo sem modelo validado.

### Protocolo obrigatório

1. Fixar pergunta e instante: prever duração total da passagem na entrada não é
   o mesmo que tempo restante para um caso já em andamento.
2. Para baseline/regressão, alvo observado sla_etapa_horas_uteis, nunca duração
   unificada estimada. Casos sem saída exigem estudo de censura/seleção separado.
3. Features apenas conhecidas na entrada: etapa/origem, calendário de entrada,
   histórico anterior comprovado. Marca/talento/cadastro só se snapshot temporal
   provar disponibilidade. Não usar IDs/nomes pessoais como atalhos preditivos.
4. Excluir features futuras: saída, duração, próxima etapa, terminal futuro,
   total final de passagens, flag de última etapa e motivos calculados no futuro.
5. Dividir por tempo e projeto_id, sem projetos nos dois conjuntos; cortar treino
   em T e incluir apenas rótulos que já estavam disponíveis até T. Separar casos
   que cruzam fronteiras e fazer backtests em janelas posteriores, com grupo.
6. Encoders, imputação, seleção e limiares ajustados só no treino. Não embaralhar
   linhas do mesmo projeto em validação aleatória. Reservar teste final intocado.
7. Reportar por ambiente/status, cobertura de projetos, MAE, quantis/calibração,
   incerteza, amostra e desempenho contra baseline; não usar MAPE com zeros.
8. ViU2 pode servir para pesquisa histórica, mas desempenho ali não prova
   generalização Globocorp. Amostra Globocorp conferida tem apenas 25 elegíveis.
9. Teste em modo sombra antes de alertas reais; humanos revisam priorização.
   Explicações mostram associações, não causas ou culpa de pessoas.

Um modelo só é promovido se superar o baseline em validação futura e ajudar a
decisão. Definir com o gestor erro tolerável em horas e capacidade de tratar
alertas. Não prometer percentual de redução sem piloto/controlar mudanças de mix.
Monitorar erro, calibração, dados ausentes, deriva e volume por etapa; fallback
para baseline quando não houver dados suficientes ou categoria conhecida.

### Ferramentas e implantação futura

Python + pandas/scikit-learn para protótipo reproduzível, scikit-survival quando
houver censura válida. Notebooks para exploração; código testado para produção.
BigQuery ML é alternativa para regressão/árvores usando SQL se simplificar a
manutenção; não é necessário contratar outra plataforma agora. Cloud Run diário
para scoring só depois de aprovação e contrato de saída; resultado com versão
do modelo, instante de previsão, intervalo/probabilidade e motivo/fallback.
Nenhum serviço online ou nova tabela de predições será criado nesta entrega.

## 4. Como apresentar à gestão

Mensagem: "Agora conseguimos localizar etapas com maior permanência, mostrar
quanto da informação é observado e investigar os casos certos. A próxima fase
testará previsões para apoiar prioridades, com incerteza explícita."
Demo: um projeto real com sua trajetória, visão de distribuições por etapa,
e uma decisão concreta de revisão de processo. Não apresentar 152,345h estimadas
como permanência comprovada nem atribuir a demora exclusivamente a uma equipe.
Benefício inicial mensurável: tempo gasto para consolidar o relatório, cobertura
de indicadores e ações gerenciais acompanhadas. No piloto: utilidade dos alertas,
erro de previsão e evolução do P90 com composição de casos controlada.
Não alegar ROI financeiro sem custos/receita/contrafactual. Não ranquear funcionários
com tempo de status, pois inclui espera externa e diferenças de complexidade.

## 5. Agenda e fechamento

- Quinta 24/09 após 6h: Scheduler + execução Cloud Run + publication_verified +
  corte BQ do dia esperado. HTTP 200 sozinho não basta. Depois, medidas e página executiva.
- Sexta 25/09: trajetória, qualidade, filtros, aceite com gestor e publicação BI autorizada.
- Segunda 28/09: priorizar novas tabelas por pergunta gerencial; definir origem,
  grão, chave, calendário, histórico, contrato, testes e destino antes de coletar.
- ML: discovery/baseline após homologação do dashboard, sem prazo prometido de
  produção enquanto cobertura e validação temporal não forem demonstradas.

## Referências técnicas consultadas

- [Conector BigQuery para Power BI](https://learn.microsoft.com/en-us/power-query/connectors/google-bigquery)
- [Regressão quantílica e intervalos](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_quantile.html)
- [Prevenção de vazamento de dados](https://scikit-learn.org/stable/common_pitfalls.html)
- [Avaliação de sobrevivência](https://scikit-survival.readthedocs.io/en/stable/user_guide/evaluating-survival-models.html)
- [Árvores no BigQuery ML](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-boosted-tree)
