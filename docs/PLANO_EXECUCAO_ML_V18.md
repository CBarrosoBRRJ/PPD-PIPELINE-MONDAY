# Plano de execução: previsão, qualidade e otimização do orçamento — v18

Complemento do [guia de consultas e KPIs](CONSULTAS_GESTAO_SLA_E_ML_V18.md).
Referência dos contratos: 25/09/2026. Este é um plano de desenvolvimento e
avaliação; nenhum modelo foi treinado e nenhuma tabela foi criada nesta revisão.
Valores de metas, duração de pilotos e capacidade de triagem são **propostas**,
a aprovar com quem opera o processo após conhecer o baseline.

## 1. Escolher a decisão antes do algoritmo

| Prioridade | Decisão | Produto esperado | Prontidão com as bases atuais |
|---|---|---|---|
| P0 | Onde agir hoje para melhorar prazo e qualidade? | Painel de fila, etapas, cobertura e lista de casos. | Consultas disponíveis; homologar execução e interpretação. |
| P1 | Qual faixa de prazo esperar de um orçamento novo? | P50/P90 de prazo e indicação de confiança. | Rótulos observados disponíveis no recorte; cadastro histórico na Entrada precisa de evidência. |
| P1 | Qual caso ativo merece revisão primeiro? | Lista de até K casos com risco, contexto e ação humana. | Requer snapshots conhecidos em T e acompanhamento confiável de abertos. |
| P2 | Quando um cliente tende a retornar? | Probabilidade de retorno por horizonte, por grupo de pedidos. | Status é aproximação; validar marco de retorno e desfechos concorrentes. |
| P2 | Quantos novos pedidos devem chegar? | Faixa semanal de demanda por grupo suficientemente frequente. | Universo atual é seletivo; criação de cópia migrada não é pedido novo. |
| P2 | Quais problemas de dados corrigir primeiro? | Fila de revisão com probabilidade de erro confirmado e impacto. | Regras existentes são baseline; falta histórico de revisão humana para supervisionado. |
| P3 | Qual briefing tem risco de revisão evitável? | Checklist direcionado antes da produção. | Falta classificar motivo da revisão e registrar briefing na Entrada. |
| P3 | Qual política de fila ou capacidade usar? | Simulador comparando cenários de equipe e prioridade. | Falta esforço ativo, disponibilidade e histórico de decisões. |

O ganho deve ser definido como uma mudança operacional mensurável: menor
P90, menor idade dos abertos, menos retrabalho confirmado ou mais casos de
qualidade resolvidos por hora de revisão. Acurácia sozinha não demonstra ganho.

## 2. Dados disponíveis, chaves e o que ainda precisa ser registrado

| Fonte | Campos/uso efetivo | Preparação necessária | Restrição para modelagem |
|---|---|---|---|
| `monday_ciclos_orcamento` | `projeto_id`, `ciclo_id`, `tipo_ciclo`, `numero_ciclo`, `inicio_utc`, `fim_utc`, `situacao`, tempos, flags de qualidade e `corte_utc`. | Uma linha por ciclo; separar primeira elaboração/revisão; identificar rótulo observado. | Fim e duração são alvos/resultados, nunca features na abertura. |
| `monday_sla_orcamento` | `interval_id`, `ciclo_id`, status, entradas/saídas, categoria, origem da duração, grupo de permanência. | Uma linha por passagem; construir somente trajetória conhecida até T. | Não usar passagens futuras nem `sla_retorno_status` que só ficou conhecido depois de T. |
| Cadastro dentro do SLA | `cadastro_atual_marca`, `talento_nome_atual`, `eh_interveniencia`, `cadastro_atual_tipo_input`, `cadastro_atual_tipo_projeto`, listas de responsáveis. | Disponibilizar versão vigente na previsão, com horário de captura. | Valores de hoje associados a ciclos antigos causam vazamento. |
| `monday_backlog_agenciamento_2026` | `board_id`, `item_id`, `status_nome`, tipo de input/projeto/output, pessoas, criação/atualização e captura. | Chave composta board+item; preservar sequência de snapshots para uso futuro. | Snapshot atual não contém valores antigos e pode omitir itens removidos. |
| `monday_talentos_exclusivos` | ID de cadastro, nome artístico, vínculo e equipes atuais. | Homologar relação de ID do talento com o projeto antes do enriquecimento. | Nome parecido não é chave; não há medida de capacidade nem performance de trabalho no JSON de equipe. |
| `monday_fila_precificacao` | ID do projeto, entrada na fila, referência de espera e horas. | Recorte de fila só em Entrada, deduplicado por projeto. | Não representa toda a carga nem todos os pedidos da empresa. |
| `monday_sla_baixa_qualidade_de_dado` | Motivos e evidências por projeto. | Ligar pelo `projeto_id`, sem multiplicar passagem por motivo. | Motivo é diagnóstico, não rótulo humano de erro confirmado. Pode coexistir com SLA. |
| Origens ViU2/Globocorp e log ViU2 | Eventos/passagens para comprovar marcos e identidade. | Consultar linhagem para casos duvidosos; preservar ambiente. | Não unir por nome nem usar estimativa de migração como verdade do alvo. |

### Ficha de um exemplo de previsão

Campos abaixo são o **formato proposto de um conjunto de experimento**, não
colunas já disponíveis em uma nova tabela do BigQuery:

| Campo lógico | Significado |
|---|---|
| `projeto_id`, `ciclo_id`, `instante_previsao` | Identidade do exemplo; IDs ficam fora da matriz de features. |
| `captura_disponivel_em` | Quando a informação de entrada realmente podia ser consultada. |
| `versao_regra`, `versao_calendario`, `versao_features` | Reproduzir cálculo e alterações de contrato. |
| `features_em_T` | Somente atributos e eventos disponíveis antes ou no instante da decisão. |
| `desfecho`, `horas_ate_desfecho`, `observado_ate` | Entrega, interrupção ou seguimento ainda aberto. |
| `rotulo_disponivel_em` | Quando a entrega/desfecho passou a estar disponível para treino. |
| `particao_temporal` | Treino, validação ou teste final, definidos antes do ajuste. |

Não basta `evento_em <= T`: a captura pode ter chegado depois. Um log resgatado
em setembro não poderia ter alimentado uma previsão real em janeiro. Para
backtest retrospectivo, explicitar se a simulação supõe disponibilidade
reconstruída; medir capacidade operacional real com coleta prospectiva.

## 3. Passo a passo comum a todos os experimentos

1. **Registrar hipótese.** Exemplo: “na triagem diária, um ranking de K=10
   casos identifica mais bloqueios acionáveis que ordenar só pela idade”.
   K=10 é exemplo; a liderança define a capacidade real.
2. **Definir população e instante.** Primeira elaboração na Entrada, revisão
   na reabertura ou ciclo ativo no corte diário. Não misturar sem identificar.
3. **Auditar evidência.** Excluir do rótulo de duração observada estimativas,
   lacunas e limites não comprovados; contar e reportar tudo que ficou fora.
4. **Construir o conjunto.** Agregar eventos até T, ligar somente dimensões
   historicamente disponíveis, deduplicar chaves e distinguir valor faltante.
   Zero horas úteis pode ser válido; desconhecido continua ausente.
5. **Congelar partições.** Ordem temporal; nenhum dado de desfecho conhecido
   depois da data de treino pode ensinar o modelo naquela simulação.
6. **Medir baseline.** Mediana/quantil, regra de idade, contagem recente ou
   checklist, usando exatamente o mesmo conjunto de teste do candidato.
7. **Treinar candidato simples.** Transformações/categorias/imputação ajustadas
   apenas no treino; guardar versão, parâmetros e semente quando aplicável.
8. **Avaliar sem retocar o teste.** Reportar métricas globais, por segmento,
   incerteza e cobertura; ajustar somente com validação anterior ao teste.
9. **Rodar em sombra.** Registrar previsão e o que o operador faria, sem
   alterar automaticamente a prioridade. Esperar os rótulos amadurecerem.
10. **Pilotar ação e ganho.** Comparar regra atual e proposta; registrar se a
    ação foi realmente executada. Medir impacto no processo e custo de manutenção.

Separar treino e teste antes de ajustar transformações evita vazamento; uma
`Pipeline` pode manter esse procedimento consistente. Ver
[orientação oficial do scikit-learn](https://scikit-learn.org/stable/common_pitfalls.html).

### Divisão temporal e independência

Proposta inicial: reservar os meses finais para teste e usar janelas anteriores
para treino/validação. O número de meses depende da frequência e do tempo de
maturação. Não usar porcentagem aleatória de linhas como avaliação principal.

- Para **projetos novos**, manter todos os ciclos de um projeto na mesma
  partição e testar somente projetos que começaram depois da fronteira. Se
  um projeto atravessar períodos, retê-lo em um grupo sem espalhar seus ciclos.
- Para **revisões de projetos conhecidos**, criar um segundo teste explícito:
  histórico anterior pode ser feature se já estava disponível, mas nenhuma
  revisão futura ou seu desfecho pode voltar para o treino.
- Para **estados diários**, várias linhas do mesmo caso são correlacionadas;
  reamostrar por projeto e separar sequências por tempo. Registrar se está
  avaliando casos novos ou atualização de risco do mesmo caso.
- Treinar em T exige que o rótulo já estivesse disponível em T. Eventos
  fechados depois são acompanhados, censurados quando aplicável ou excluídos
  daquele treino; nunca revelados antecipadamente.

## 4. Modelo A — faixa de prazo na abertura do ciclo

### Objetivo e dados

**Decisão:** orientar uma expectativa de entrega e identificar pedidos que
precisam de planejamento específico. Há dois alvos distintos:

1. **Prazo percebido:** `(fim_utc-inicio_utc)` em horas corridas até o marco de
   Feedback, em ciclos com evidência observada. Inclui esperas antes da entrega.
2. **Permanência operacional:** `operacao_horas_uteis`, que inclui Entrada,
   elaboração e revisão operacional. Ajuda a entender processo; não se
   converte diretamente em data de entrega porque exclui esperas externas.

Começar com `tipo_ciclo` e atributos de calendário do início. Marca, talento,
tipo de input/projeto e complexidade entram quando comprovadamente disponíveis
na abertura. O dataset atual permite explorar alvos; não garante automaticamente
o histórico de todas essas features.

### Consulta para inspecionar rótulos e calendário

```sql
SELECT projeto_id, ciclo_id, tipo_ciclo, numero_ciclo,
  inicio_utc, fim_utc, corte_utc, situacao,
  EXTRACT(DAYOFWEEK FROM DATETIME(inicio_utc, 'America/Sao_Paulo'))
    AS dia_semana_inicio,
  EXTRACT(HOUR FROM DATETIME(inicio_utc, 'America/Sao_Paulo'))
    AS hora_inicio,
  IF(kpi_entrega_observada,
    TIMESTAMP_DIFF(fim_utc, inicio_utc, SECOND) / 3600.0, NULL)
    AS alvo_janela_horas_corridas,
  IF(kpi_entrega_observada, operacao_horas_uteis, NULL)
    AS alvo_operacao_horas_uteis,
  kpi_entrega_observada, contem_estimativa, contem_idade_aberta,
  duracao_completa, versao_regra, versao_calendario
FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_ciclos_orcamento`;
```

Selecionar explicitamente as features permitidas; **não treinar com todas as
colunas retornadas**. `fim_utc`, `situacao`, flags finais, duração completa e
alvos revelam o desfecho. IDs servem para joins, deduplicação e partições.

### Implementação em etapas

1. Auditar a seleção de ciclos observados. Comparar seu mix com abertos,
   interrompidos e excluídos; o modelo de encerrados pode subestimar casos longos.
2. Criar baseline de P50/P90 por tipo de ciclo no treino, com fallback global
   quando o segmento não tiver amostra suficiente. Usar quantil das observações,
   não média de quantis calculados em pequenos grupos.
3. Testar regressão quantílica regularizada; só depois avaliar gradient boosting
   quantílico. Uma opção Python é `HistGradientBoostingRegressor` com perda
   `quantile`, um ajuste por quantil. Escolher complexidade por validação temporal.
4. Tratar categorias raras no treino; categorias novas na previsão recebem
   grupo desconhecido. Não usar codificação pela média do alvo com informações
   do teste. Se houver target encoding, respeitar a ordem temporal no treino.
5. Produzir P50 e P90 não negativos e verificar `P90 >= P50`. Cruzamento de
   quantis deve ser corrigido por procedimento definido na validação, avaliado
   novamente e registrado; não ajustar manualmente caso a caso no teste.
6. Na apresentação, mostrar faixa/quantil, população e nível de suporte. P90
   é limite superior probabilístico de 90%, não garantia contratual.

### Métricas e meta candidata

- MAE do P50, em horas, para erro típico; comparar com baseline no mesmo teste.
- Pinball loss de P50 e P90 para avaliar quantis. Menor é melhor.
- Cobertura superior P90 = proporção de alvos `<= P90_previsto`, esperada perto
  de 90%; quantil calibrado demais para cima gera promessa pouco útil.
- Se houver P10 e P90, o intervalo central esperado é de **80%**, não 90%.
  Medir largura junto da cobertura; não aprovar intervalo arbitrariamente amplo.
- Segmentar por tipo de ciclo, período, faixa de duração e grupos com volume.

**Proposta de aceite técnico:** MAE e pinball P90 pelo menos 10% menores que
o baseline no teste futuro; cobertura P90 entre 85% e 95%, interpretada com
intervalo de confiança e N. Segmentos pequenos usam baseline e aviso de pouco
suporte. Esses limites são proposta de piloto, não regra estatística universal.
**Aceite de negócio:** reduzir incerteza da triagem e melhorar K01 sem piorar
idade dos abertos ou volume. Um modelo preciso sozinho não acelera a equipe.

## 5. Modelo B — risco de demora nos ciclos em andamento

### Objetivo, alvo e unidade

**Decisão diária:** quais K ciclos revisar para desbloquear o fluxo? Uma linha
por ciclo e instante T. Alvo: probabilidade de entrega nos próximos 2/5/10 dias
úteis, definidos pelo calendário do pipeline, ou distribuição do tempo restante.
“Atraso” exige prazo pactuado; sem ele chamar de risco de permanência longa.

Features: status/categoria conhecidos em T, idade do ciclo e da etapa, número
de retornos já ocorridos, tempo operacional acumulado conhecido, esperas já
encerradas e, futuramente, WIP/capacidade e prioridade conhecidos nesse momento.
As tabelas atuais não guardam automaticamente todos os retratos usados nas
previsões de dias anteriores; confirmar arquivos de publicação disponíveis ou
iniciar registro prospectivo para reconstrução reproduzível.

### Censura e interrupções

Um ciclo ainda aberto no fim do acompanhamento é censurado à direita **se
houver evidência de que foi acompanhado até ali**. Lacuna de log é falta de
evidência, não censura comprovada. Um ciclo interrompido/cancelado é um desfecho
concorrente à entrega; não o tratar automaticamente como censura independente.
Definir entrega versus interrupção com o negócio e, quando houver volume,
avaliar risco competitivo ou modelar explicitamente ambos os desfechos.

### Passo a passo

1. Definir horário de corte e formar exemplos com features de T, mantendo a
   sequência de cada projeto e o momento em que cada informação chegou.
2. Baseline operacional: ordenar por idade e, separadamente, estimar chance
   de entrega por status/faixa de idade usando somente treino.
3. Para população com censura tratável, começar com sobrevivência simples;
   testar Cox regularizado e avaliar pressupostos. Modelos de floresta só se
   o volume/validação justificarem. Para evento concorrente, usar método e
   métrica compatíveis com a probabilidade de entrega definida.
4. Produzir probabilidade por horizonte, motivo contextual e próximo passo
   para revisão humana. Importância de feature não identifica causa da demora.
5. Comparar lista de K casos com a lista por idade e verificar se a liderança
   encontrou bloqueio acionável. Registrar ação e tempo de revisão.

### Avaliação e proposta de aceite

Para sobrevivência com censura à direita, usar Brier dependente do tempo/IPCW,
calibração por horizonte e C-index como medida complementar de ordenação.
Escolher horizontes dentro do suporte de seguimento; não extrapolar além do
que o conjunto de avaliação permite. O [guia de avaliação de sobrevivência](https://scikit-survival.readthedocs.io/en/stable/user_guide/evaluating-survival-models.html)
discute essas métricas e limitações.

Para a decisão, medir `precision@K` de casos realmente acionáveis, recall dos
problemas encontrados e minutos de revisão por caso útil. Esse rótulo exige
confirmação humana; não confundir demora futura com bloqueio solucionável.

**Meta técnica proposta:** reduzir Brier no horizonte prioritário em 10%
contra baseline e aumentar casos acionáveis por K em 20%, com incerteza
reportada. **Meta de processo:** piloto de triagem reduz P90 da idade dos
abertos em 15%, acompanhando throughput e não deixando casos fora do ranking
sem revisão. Se não houver rótulo de ação útil, medir risco preditivo e manter
o ganho operacional como pendência de piloto.

## 6. Modelo C — previsão de espera por Feedback

**Decisão:** planejar devolutiva e contato comercial. Unidade: uma permanência
em Feedback após envio. Alvo ideal: tempo entre envio e resposta explícita do
cliente. Alvo disponível: transição para fora de Feedback, que é aproximação.
Uma saída para encerrado pode ser cancelamento administrativo, não resposta.

**Dados:** passagens `feedback`, projeto/ciclo, início, fim observado, origem
da duração, marca/tipo de projeto conhecidos no envio. Usar grupo de permanência
para avaliar uma espera contínua dividida entre ambientes; se houver estimativa
no grupo, não rotulá-la como tempo totalmente observado.

1. Confirmar quais transições significam retorno real; separar encerramentos
   e cancelamentos. Começar uma coleta do evento de resposta, se necessário.
2. Baseline: mediana/P90 por grupo comercial no treino, com fallback global.
3. Tratar esperas ainda abertas por sobrevivência quando a evidência permitir;
   usar regressão de quantis apenas para alvo e seleção explicitamente definidos.
4. Exibir chance de retorno até o horizonte e lista de contatos a revisar,
   incluindo amostra e incerteza para marcas pouco frequentes.
5. Pilotar um rito de contato pactuado; registrar quem contatou e quando para
   diferenciar performance do modelo do efeito da intervenção.

**Métricas:** pinball/MAE se duração observada; Brier/calibração por horizonte
se sobrevivência, além de casos úteis por contato. **Meta proposta:** ganho
de pelo menos 10% contra baseline preditivo e redução de 10% no P90 de espera
do grupo-piloto, sem aumento de contatos considerados desnecessários pela área.
O ganho será investigado; não é resultado garantido nem já observado.

## 7. Modelo D — previsão de demanda semanal

**Decisão:** antecipar volume de novos pedidos para triagem e planejamento.
Unidade: semana completa × grupo de demanda. Alvo: pedidos novos distintos,
não quantidade de passagens ou revisões. Se a população for o SLA, usar primeira
Entrada reconhecida por projeto e declarar seleção; para demanda corporativa,
precisa de universo de solicitações completo e vínculo das migrações.

`criado_em_origem` do backlog pode ser a criação da cópia após migração. Não
chamá-la de criação comercial do projeto sem validar. Snapshot atual também
não garante que itens removidos no passado estão presentes.

1. Homologar evento de pedido novo e a cobertura ao longo do calendário.
2. Construir semanas completas e distinguir semana comprovadamente com zero
   pedidos de semana sem coleta. Fechar calendário de feriados/eventos conhecidos.
3. Baselines: semana anterior, média das últimas 4 semanas e regra sazonal
   quando houver histórico suficiente para estimar a sazonalidade.
4. Avaliar série temporal simples ou regressão de contagem com lags conhecidos
   na data de previsão. Fazer backtest de origem móvel para horizontes de
   1 e 4 semanas; não usar valores futuros como lags ou médias móveis centradas.
5. Começar pelo total; abrir grupos somente quando a amostra sustentar o
   recorte. Reconciliar soma dos grupos e total se modelos forem independentes.
6. Entregar faixa de demanda e risco de pico, junto da capacidade planejada
   quando ela existir. Previsão de volume não determina automaticamente pessoas.

**Métricas:** MAE em pedidos/semana; WAPE = soma dos erros absolutos / soma dos
pedidos reais, indefinido quando o total real é zero; erro em semanas de pico;
cobertura/largura do intervalo. Evitar MAPE com semanas de zero ou pouco volume.

**Meta proposta:** reduzir MAE em 10% contra o melhor baseline no mesmo
backtest, mantendo cobertura adequada e sem piorar sistematicamente picos.
Para sazonalidade anual, exigir histórico que permita verificá-la; semanas
recentes isoladas não demonstram um padrão anual. **Benefício a testar:** menos
sobrecarga inesperada e melhor preparação de capacidade.

## 8. Modelo E — retrabalho evitável

**Decisão:** quais briefings revisar antes de iniciar a elaboração? Alvo:
revisão causada por problema evitável confirmado, dentro de uma janela
definida após envio. Reabertura comercial legítima não deve virar erro.

Faltam motivo homologado, registro de briefing na Entrada e data de confirmação
do problema. As tabelas atuais oferecem trajetórias/ciclos para auditoria e
amostragem, mas não resolvem esses rótulos sozinhas.

1. Definir taxonomia com exemplos: falta de informação, ajuste do cliente,
   mudança de escopo, correção interna e não informado.
2. Revisar amostra com dois avaliadores e resolver divergências; guardar
   instrução de rotulagem. Avaliar concordância, inclusive por tipo de problema.
3. Definir janela de acompanhamento, por exemplo 30 dias após envio, aprovada
   pela área. Casos com menos seguimento não são automaticamente negativos.
4. Baseline: checklist de briefing. Candidato: regressão logística regularizada
   com features disponíveis na entrada; depois boosting se houver ganho estável.
5. Escolher limiar/K pela capacidade de revisão e custo de erro, com ajuste
   em validação. Probabilidade pode precisar de calibração separada.

**Métricas:** average precision (informar implementação; não misturar com área
trapezoidal de curva PR), `precision@K`, recall, Brier/calibração, revisões úteis
por hora. Acurácia pode parecer alta quando quase todos os pedidos não têm erro.
**Meta proposta:** 20% mais defeitos confirmados encontrados na mesma capacidade
de revisão versus checklist, sem aumentar indevidamente o prazo de entrada.
**Ganho de negócio:** redução de revisão evitável; medir esforço ativo poupado
somente quando houver apontamento confiável de trabalho.

## 9. Modelo F — priorização de qualidade dos dados

**Decisão:** que caso investigar primeiro para recuperar informação útil?
Começar pelas regras e motivos já publicados. Categoria rara ou duração longa
não é, por si, erro de dado.

1. Listar projetos com motivos, impacto na métrica e possibilidade de correção.
2. Definir fila por severidade/impacto/idade como baseline transparente.
3. Registrar classificação humana: confirmado, válido, inconclusivo; causa,
   ação, tempo gasto e evidência de correção. Não descartar inconclusivos como
   negativos sem justificativa.
4. Com rótulos suficientes, testar ranking supervisionado. Sem rótulos,
   detector de anomalia serve apenas para ampliar revisão amostral.
5. Validar correção na publicação seguinte e conferir se a identidade e o
   histórico continuam consistentes. Não aprender somente dos casos escolhidos
   pelo modelo: manter amostra independente para estimar erros ignorados.

**Métricas:** casos confirmados por K, minutos por correção útil, reincidência,
tempo até resolução e projetos que ganharam evidência utilizável. **Meta
proposta:** 20% mais casos úteis por hora versus fila por regra, acompanhando
falsos positivos. Não definir meta de “zerar diagnósticos” removendo regras.

## 10. Modelo G — simulação de fila e otimização de capacidade

**Decisão:** testar o efeito de redistribuir capacidade, limitar WIP, mudar
triagem ou criar cobertura por especialidade. Simulação de eventos discretos
e otimização com restrições podem ser mais adequadas que ML para essa pergunta.

**Dados necessários:** chegadas reais, rotas, esforço ativo/tempo de serviço,
capacidade por equipe e calendário, bloqueios externos, prioridades, retrabalho
confirmado e decisões de alocação. Hoje o tempo em status inclui espera interna
e não pode ser usado diretamente como tempo de serviço de um profissional.

1. Mapear fluxo e recursos com a equipe; escolher uma célula/rota piloto.
2. Estimar distribuições de chegada e serviço ativo a partir de evidência.
   Enquanto serviço não existe, usar cenários hipotéticos explícitos e análise
   de sensibilidade; não afirmar dimensionamento ótimo da equipe.
3. Reproduzir cenário atual, comparando fila, throughput e P50/P90 observados.
4. Testar poucas políticas: limite de WIP, cobertura em pico, triagem por
   complexidade ou prioridade pactuada. Respeitar habilidades e disponibilidade.
5. Rodar repetições para medir variabilidade e cenários de demanda/ausência.
6. Pilotar uma mudança reversível e medir efeito real. Um simulador que não
   reproduz o fluxo atual não deve sustentar promessa de ganho.

**Métricas:** erro de reprodução do cenário atual, P90 de espera, throughput,
WIP, ocupação com tempo ativo medido e equidade de carga entre células.
**Meta proposta:** reduzir P90 da fila em 15% no cenário e validar o ganho no
piloto sem piora >5% em entregas nem aumento relevante de retrabalho confirmado.
Limites de ocupação devem ser pactuados conforme variabilidade e capacidade;
100% de ocupação não é uma meta automática de um sistema de filas.

## 11. Dicionário de métricas e como interpretar

| Métrica | Cálculo/leitura | Uso e armadilha |
|---|---|---|
| MAE | Média de `abs(real-previsto)`, na unidade do alvo. | Prazo em horas ou volume em pedidos. Não misturar relógios. |
| Pinball em q | Média de `max(q*(real-previsto), (q-1)*(real-previsto))`. | Avalia quantil q; menor é melhor. Usar q igual ao previsto. |
| Cobertura superior P90 | Fração com real ≤ P90 previsto. | Esperada perto de 90%; acompanhar amplitude/valor do quantil. |
| Precision@K | Casos positivos confirmados entre os K revisados / K revisado. | Eficiência da fila humana; declarar qual é o positivo. |
| Recall | Positivos encontrados / positivos reais avaliáveis. | Exige conhecer também casos fora da lista priorizada. |
| Brier binário | Média de `(probabilidade-resultado_0_ou_1)^2`. | Probabilidade; com censura, usar versão ajustada ao horizonte. |
| Calibração | Frequência real versus probabilidade prevista por faixa. | 70% previsto deve corresponder aproximadamente a 70% no grupo. |
| C-index | Capacidade de ordenar tempos de evento comparáveis. | Não prova calibração nem utilidade da lista de ação. |
| WAPE | Soma dos erros absolutos / soma dos reais. | Volume; denominador zero torna a medida indefinida. |
| Ganho relativo | `(erro_baseline-erro_modelo)/erro_baseline`. | Mesmo teste e população; indefinido se erro baseline=0. |

MAE avalia previsão de mediana; pinball avalia quantis. Métricas probabilísticas
e de decisão respondem perguntas diferentes. Consulte a
[documentação de métricas do scikit-learn](https://scikit-learn.org/stable/modules/model_evaluation.html)
para a implementação escolhida. Todas as faixas de aceite neste documento são
propostas do projeto e devem ser congeladas antes de abrir o teste final.

### Relatório mínimo de um experimento

Preencher: hipótese; população; instante T; período de treino/validação/teste;
N de projetos/ciclos; contagem de eventos/censuras; excluídos por motivo;
features e disponibilidade; baseline; candidato e parâmetros; métricas com
incerteza; segmentos com pouco suporte; custo; limitações; decisão de avançar.

Exemplo **hipotético**: baseline MAE=20h e candidato=17h → melhoria de 15%.
Se cobertura P90 for 60%, a previsão ainda está mal calibrada e não satisfaz
a proposta de aceite. Se a equipe não consegue agir sobre o resultado,
ganho preditivo pode não trazer ganho de processo.

## 12. Marcos, operação e avaliação do benefício

| Etapa | Entrega | Aceite proposto | Responsável sugerido |
|---|---|---|---|
| Dados elegíveis | Inventário, rótulos e auditoria de disponibilidade em T. | Zero uso de features futuras; chaves/joins verificados; limitações registradas. | Engenharia + analista de negócio. |
| Baseline | Previsões de regra simples em partições temporais. | Reproduzível; unidade, período e população aprovados. | Analista/cientista de dados. |
| Candidato | Código/configuração e teste final congelado. | Atende metas específicas do modelo e não degrada grupos relevantes sem justificativa. | Ciência de dados + operação. |
| Sombra | Registro de previsão, decisão sugerida e desfecho. | 2–4 semanas como ponto de partida, ampliadas até haver desfechos suficientes; custo e revisão viáveis. | Operação + dados. |
| Piloto assistido | Uma intervenção definida, grupo comparável e registro de ação. | Ganho de processo com incerteza avaliada e condições de qualidade mantidas. | Dono do processo. |
| Operação contínua | Responsável, alertas, versão, rotina de revisão e retorno ao baseline. | Campos/corte válidos, previsões reproduzíveis e monitoramento ativo. | Engenharia + dono do produto. |

### Como medir benefício sem confundir correlação com efeito

1. Escolher uma ação e uma métrica principal antes do piloto. Se mudar
   briefing, equipe e prioridade ao mesmo tempo, a causa do ganho fica difícil
   de separar.
2. Quando viável, distribuir pedidos/equipes comparáveis entre rotina atual
   e proposta; controlar interferência porque equipes compartilham capacidade.
   Se houver implantação faseada, registrar as diferenças e limitações.
3. Medir intenção de aplicar e aplicação real. Caso recomendado e não tratado
   não demonstra que a ação sugerida funcionou ou falhou.
4. Comparar P90, volume, qualidade, idade dos abertos e carga de revisão. Estimar
   incerteza com unidade de amostragem compatível (projeto/equipe/período).
5. Converter ganho financeiro somente com custo real e esforço medido:
   benefício líquido = custo evitado comprovado − custo de dados/modelo/ação.
   Redução de horas corridas não equivale a redução de horas de salário.

### Monitoramento e retorno à regra simples

- Em cada execução: conferir esquema, corte, ausência de features essenciais,
  categorias novas, cobertura da previsão e valores fora do domínio.
- Semanalmente: revisar N de casos acionáveis, tempo gasto e feedback dos
  usuários. Não recalibrar pelo teste final repetidamente.
- Com rótulos maduros: acompanhar MAE/pinball/Brier e calibração por coorte
  de previsão. Métrica dos últimos dias com poucos desfechos é provisória.
- Gatilho proposto de revisão: erro >20% acima do baseline em duas janelas
  maduras com amostra suficiente, ou mudança relevante de contrato/população.
  Investigar dados/mix antes de treinar de novo.
- Falta de campos críticos ou contrato incompatível: suspender a previsão
  daquele caso e usar baseline/triagem humana com sinalização de indisponibilidade.
  Guardar previsão original e motivo, para auditoria posterior.

## 13. Ordem recomendada para começar

Na primeira etapa, homologar as consultas e o painel de confiança, escolher um
gargalo e medir o baseline. Em paralelo, registrar os dados na Entrada e os
eventos de envio/resposta com seus horários de disponibilidade. Com esses
dados, executar o Modelo A em sombra e a triagem por regra como comparação
para o Modelo B. A previsão de demanda entra quando a série de pedidos novos
estiver reconciliada. Retrabalho e capacidade avançam após seus novos eventos
de controle estarem disponíveis e homologados.

Essa ordem vincula cada investimento de dados a uma decisão operacional e
permite interromper um modelo que não supera uma regra simples, preservando
o painel e as melhorias de processo já úteis à equipe.
