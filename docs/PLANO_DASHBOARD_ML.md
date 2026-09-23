# Gestão do fluxo: entregar mais rápido, com qualidade

Plano revisado em 23/09/2026. Objetivo: reduzir tempo do primeiro status até a
conclusão, encontrar gargalos, melhorar processo e equipe. Não apenas exibir médias.
Este é um projeto analítico, não homologação de novos KPIs. A v12 permanece em
produção. Protótipo com dados fictícios; nenhuma nova leitura BQ foi realizada.

[Protótipo navegável](../powerbi/sla_gestao/prototipo.html) ·
[Implementação Power BI/HTML Content](../powerbi/sla_gestao/IMPLEMENTACAO.md) ·
[Diagnóstico SQL](../tabelas/monday_sla_orcamento/sql/diagnostico_ponta_a_ponta.sql)

## 1. Começar pela decisão, não pelo gráfico

**Estamos entregando mais rápido, com menos repetição e sem perder qualidade?**

1. Resultado: tempo do ciclo, previsibilidade, quantidade concluída e qualidade.
2. Diagnóstico: concentração de tempo, filas, aprovações, retornos e variabilidade.
3. Ação: revisar briefing, rito de feedback, prioridade, handoff ou capacidade.
4. Controle: o tempo caiu sem aumentar revisões, recusas ou casos antigos esquecidos?

Cada KPI tem dono, cadência, gatilho e ação. O responsável pelo processo deve
escolher semanalmente um problema, revisar casos e conduzir um teste de melhoria.
Os nomes dos responsáveis e metas devem ser pactuados, não inventados pelo painel.

**Etapa demorada é candidata a gargalo.** Gargalo é a restrição que limita a saída
do sistema; confirmar exige evidência de fila, demanda, capacidade e execução.
Tempo em status inclui espera externa. Não mede esforço, produtividade individual
ou culpa do responsável atual. Reduzir uma etapa pode apenas deslocar a fila.

## 2. Primeiro ao último: qual relógio queremos gerir?

| Medida | Início → fim | Interpretação |
|---|---|---|
| Lead time do processo | Entrada comprovada → primeiro terminal do ciclo | Quanto demorou para fechar o processo |
| Tempo até entrega | Entrada → evento confirmado de orçamento entregue | Quanto o cliente esperou; exige identificar esse evento |
| Permanência por etapa | Entrada → saída da etapa | Onde houve tempo dentro do fluxo |
| Janela observada | Primeira → última observação disponível | Período documentado; não comprova começo/fim do processo |

Encerrado não comprova entrega comercial. Declinados encerram processos, mas não
são entregas bem-sucedidas. Separar desfechos; até validar entrega, usar o título
"tempo até encerramento do processo". Misturar recusas rápidas pode melhorar uma
média artificialmente. O último status pode estar aberto e o primeiro ser uma
cópia no meio do fluxo: MIN/MAX sem qualificação não homologa ponta a ponta.

Regra proposta: uma Entrada comprovada até o primeiro terminal daquele ciclo.
Reabertura cria outro ciclo observável, sem estender silenciosamente o anterior.
Para entrega final após reaberturas, definir outro indicador e sua fronteira.

### Corridas, úteis e trabalho efetivo

Horas corridas: diferença UTC / 3.600 segundos. Horas úteis: interseção com seg-sex
10–13/14–19, São Paulo, feriados BR PUBLIC e extras configurados. Reusar calendário
versionado Python; não dividir corridas por 8 nem calcular apenas dias no DAX.
Exemplo sem feriado: sexta 18h → segunda 11h = **65h corridas e 2h úteis**.
Corridas medem espera no relógio; úteis, permanência no expediente. Nenhuma prova
esforço realmente trabalhado. Carnaval/Corpus Christi não são excluídos automaticamente.

Em cadeia contínua, sem sobreposição, no mesmo calendário, soma das durações =
duração do ciclo (com tolerância de arredondamento documentada). Lacuna aparece
como tempo não atribuível, não zero; sobreposição não deve ser contada duas vezes.
Somar medianas/P90 das etapas NÃO produz a mediana/P90 do ciclo.

### O que a tabela permite hoje

| Uso | Campo/evidência | Estado |
|---|---|---|
| Tempo de etapa observado | sla_etapa_horas_uteis | Disponível |
| Etapa com hipótese de fronteira | duracao_analise_horas/horas_uteis + origem_duracao_analise | Disponível, não fato comprovado |
| Ciclo completo dentro da origem | tempo_ciclo_observado_horas | Disponível quando a cadeia local foi conectada; horas corridas |
| Ciclo global entre contas | Identidade, endpoints e regra de ciclo homologados | Não aprovado no contrato atual |
| Entrega ao cliente | Evento de entrega aprovado | Não inferir de terminal |
| Backlog/idade atual | Estado atual e captura confiáveis | Não inferir de NULL histórico |

O ciclo local aparece apenas no primeiro terminal da cadeia. Conferir cobertura
no diagnóstico SQL antes de usá-lo; não renomear como ciclo global. Há zero
continuidade_validada no recibo conferido. "Sem lacunas detectadas" também não
homologa completude vitalícia. O objetivo ponta a ponta é correto, mas essa parte
exige evolução de contrato/evidência, não apenas outro gráfico.

Endpoints confiáveis permitem medir uma janela mesmo quando faltam etapas no
meio. Isso não autoriza atribuir todo o tempo a uma equipe. Qualidade dos endpoints
e qualidade da decomposição são aprovações distintas. A tabela ainda não possui
homologação pública desses endpoints globais; não contornar isso por DAX.

### Contrato de ciclo proposto, ainda não implementado

Grão: projeto_id + ciclo_id + escopo_ciclo (origem/global). Campos: inicio/fim UTC,
marco_fim, desfecho, horas corridas/úteis, qualidade_endpoints, qualidade_decomposicao,
tempo_sem_atribuicao, tem_estimativa, regra_ciclo e versao_calendario.
Classes: observado_aprovado; janela_com_endpoints_aprovados; analitico_estimado;
incompleto. Não misturar classes no KPI principal. Contar uma vez por ciclo.
Validar reabertura, vínculo, calendário e cronologia; nenhuma data inventada.
Pode ser derivado no modelo BI após revisão; persistência em BQ é decisão separada.

## 3. Aula dos KPIs: significado → decisão → avaliação

### A. Lead time P50/P90: o resultado principal

Fórmula: percentis das durações dos ciclos elegíveis concluídos no período.
P50 é mediana: metade terminou até ali. P90: 90% até ali, 10% demorou mais.
Exemplo fictício: P50=48h e P90=96h úteis. Prometer 48h para todos é imprudente.
P90 histórico não é garantia individual nem meta automaticamente.
Decisão: calibrar expectativa e investigar a cauda. Se P50 cai e P90 sobe, os
casos comuns melhoraram mas os difíceis pioraram: não comemorar só a média.
Avaliação: comparar mesmo mix, origem, complexidade e desfecho; mostrar N e cobertura.
Período padrão = conclusão do ciclo. Acompanhar abertos separadamente para não
esconder sobreviventes longos. Hoje: ciclo local parcial; global depende da seção 2.

### B. Volume de saída e envelhecimento: contrapesos do tempo

Contar ciclos distintos encerrados por semana e desfecho; saídas de etapa não são
entregas de projeto. Comparar entradas/saídas e idade dos ativos quando houver
população atual confiável. Se volume cai enquanto tempo melhora, podem estar
selecionando só casos fáceis. Se a fila envelhece, o painel de concluídos é insuficiente.
Decisão: balancear prioridade/capacidade e não abandonar casos antigos.
Não publicar backlog de toda a operação com a amostra histórica selecionada.

### C. Cumprimento de prazo: somente com compromisso real

Taxa = entregues no prazo / entregues com prazo válido pactuado no início.
Versionar meta por classe e vigência; não definir depois de ver resultado.
Sem meta, mostrar "não pactuada", não semáforo de atraso. Complementar com ativos
já vencidos quando houver snapshot confiável. Decisão: escalonar exceção, revisar
promessa/capacidade. Recusa rápida não entra como entrega no prazo.

### D. Exposição por etapa: onde priorizar a investigação

E_s = soma de horas da etapa s nos mesmos ciclos completos elegíveis.
Share_s = E_s / soma de E_s. Em histórico parcial, rotular "tempo observado",
não "percentual de todo o lead time". Mostrar também passagens/ciclos, média e P90.
Uma etapa rara de 100h pode contribuir menos que 10h repetidas cem vezes.
Exemplo fictício de 120 ciclos: feedback 3.600h, validação 1.200h, elaboração 900h,
triagem 300h = 6.000h. Feedback concentra 60%; investigar antes de otimizar triagem.
Decisão: revisar casos, checar dependências/cliente/briefing e escolher um piloto.
Participação alta é pista, não prova causal de ineficiência da equipe.

### E. Retornos, primeira passagem e qualidade

Retorno observado = revisita uma etapa; não significa erro. Separar mudança de
escopo, negociação e correção de defeito com motivos aprovados.
FTR proposto = ciclos entregues e aceitos sem revisão por defeito / ciclos entregues
com trajetória e motivo confiáveis. Sem aceite/motivo, usar o proxy "sem retorno
observado" e declarar que lacunas podem esconder retornos. Não chamar de qualidade real.
Custo temporal de repetição = permanência nas segundas/posteriores visitas,
por motivo. Decisão: checklist de briefing e validação mais cedo.
Guardrail: não reduzir revisões necessárias nem incentivar ocultação de defeitos.

### F. Handoffs, espera e bloqueios

Mapear status por natureza e vigência: execução interna, aprovação interna, espera
externa, bloqueio, terminal. Aprovar dono e significado; nome do status sozinho
não prova causa ou responsabilidade. Tempo de handoff precisa envio/aceite real:
diferença entre eventos não é automaticamente fila.
Decisão: explicitar dono, rito de resposta, escalonamento e critérios de entrada.
Não chamar razão "status interno/total" de eficiência de fluxo: touch-time/lead-time
exige tempo de trabalho ativo que hoje não medimos.

### G. Comportamento de equipe com contexto

Comparar células/equipes com atribuição histórica e mix similares. Responsável
atual não comprova quem fez o trabalho anterior. Mostrar junto: volume, complexidade,
P90, retorno, fila e cobertura (os dois últimos operacionais dependem de novos dados).
Pergunta: sobrecarga, dependência externa ou briefing incompleto? Tempo isolado não responde.
Não usar esses campos para ranking disciplinar individual nem decisão automatizada.

### H. Cenário de oportunidade e melhoria efetiva

No exemplo, reduzir 20% das 3.600h de feedback = 720h de permanência acumulada,
ou 6h por ciclo em média (720/120). **Não são horas de trabalho poupadas**, nem
redução demonstrada do P90. Paralelismo e deslocamento da fila mudam o resultado.
Escolher experimento com hipótese, dono, início, coorte, métrica e guardrail.
Avaliar P50/P90, volume, retorno e idade dos abertos com mix comparável. Antes/depois
é associação; grupo comparável, randomização ou implantação faseada fortalecem
a avaliação. P90 menor com mais cancelamentos não é sucesso.

## 4. Dashboard: onepage executiva + quatro aprofundamentos

Não colocar tudo em uma tela. A página 1 funciona sozinha na reunião; as demais
permitem investigar e auditar. Cinco páginas do mesmo relatório:

| Página | Pergunta | Visuais/ação |
|---|---|---|
| Decisão | Estamos mais rápidos sem piorar qualidade? | 4 KPIs, tendência, prioridade e ação |
| Gargalos | Onde o tempo se concentra? | Pareto de exposição, frequência/P90, cenário transparente |
| Processo e equipe | Por que repetimos/esperamos? | Retornos/motivos, mix, responsabilidades verificadas e piloto |
| Projeto | O que ocorreu neste caso? | Linha do tempo com datas, lacunas e estimativas distintas |
| Confiança | Em quais dados posso confiar? | População, exclusões, origem da duração, corte, definição |

Filtros nativos: período com papel claro (conclusão/entrada), origem, desfecho e
classe de serviço quando disponível. Não unir IDs de status entre contas.
Drillthrough de projeto conserva projeto e não corta a trajetória pelo filtro
temporal, com aviso explícito. KPIs sem cobertura mostram "a validar", nunca zero.
O protótipo mostra o desenho alvo com números fictícios; não é homologação.

Power BI Import + conector BigQuery, modelo estrela. FatoPassagens atual e
FatoCiclosProposta somente quando contrato revisado; dimensões compartilhadas,
relações 1:N/unidirecionais, sem join por nome e sem multiplicar ciclos por visitas.
Atualizar depois da publicação confirmada do pipeline, não só por ter passado das 6h.
Detalhes de HTML Content, medidas e aceite no guia de implementação.

## 5. Aula de ML: prever não é provar a causa

BI explica o que ocorreu. Previsão estima o que pode ocorrer. Experimento testa
o que muda se agirmos. Um modelo que associa responsável à duração não prova
que trocar o responsável reduzirá o prazo. Priorizar utilidade, não sofisticação.

### Modelo 1 — risco de não terminar e tempo restante (prioridade futura)

Decisão: quais casos ativos devem receber revisão humana hoje? Instante: captura
diária confiável. Alvo: tempo até entrega/terminal definido, separando desfechos.
Baseline Kaplan–Meier por classe/etapa; Cox regularizado; candidato não linear
Random Survival Forest. Melhor modelo é o que vence baseline em teste futuro,
calibra riscos e cabe na capacidade de intervenção, não um algoritmo escolhido a priori.

Sobrevivência trata casos ainda não concluídos quando sabemos até quando foram
observados. NULL de histórico perdido não é censura administrativa. Para covariáveis
fixas, S(a+h)/S(a) estima chance de permanecer mais h após idade a, se S(a)>0;
atributos mutáveis exigem abordagem temporal/landmark e validação própria.
Métricas: Brier (erro probabilístico, menor melhor), calibração (previsto x observado),
C-index (ordenação, maior melhor) e precision@K (utilidade no limite de alertas).
C-index bom com probabilidade mal calibrada não autoriza promessa de prazo.
Dependências: captura atual, censura, finais e volume Globocorp. Ainda não pronto.

### Modelo 2 — expectativa de duração na entrada

Decisão: oferecer uma faixa de prazo. Baseline mediana/P90 etapa-classe; candidato
gradient boosting quantílico P50/P90. Alvo é ciclo aprovado OU etapa observada,
conforme a pergunta; somar percentis de etapas não prevê percentil do ciclo.
MAE em horas para P50, pinball loss por quantil, cobertura/largura de intervalos.
P90 deve cobrir aproximadamente 90% dos casos avaliados, não garantir cada caso.
Treinar só concluídos seleciona rápidos: explicitar viés ou usar sobrevivência.
Nunca tratar estimativa de fronteira como rótulo de verdade.

### Modelo 3 — risco de retrabalho evitável

Decisão: quais briefings revisar antes de uma devolução cara? Alvo: revisão por
defeito de briefing/cadastro, não todo retorno. Features: completude e complexidade
disponíveis no início, alterações já ocorridas e histórico anterior verificável.
Baseline checklist; regressão logística regularizada; comparar árvores.
PR-AUC, recall, precision@K e calibração; custo de alerta falso x defeito não detectado.
Motivos/aceite/completude ainda precisam fonte confiável. Sem isso, modelo aprenderia
um proxy enganoso. Explicações estatísticas não são culpa de pessoas.

### Modelo 4 — simular melhoria de capacidade e fluxo

Decisão: testar limite de WIP, rito de feedback e balanceamento. Começar pelo
cenário aritmético explícito; evolução: simulação de eventos discretos com chegadas,
filas, capacidade, prioridades, rotas e distribuições. Não é necessariamente ML.
Duração em status não mede serviço ativo/capacidade sem dados adicionais.
Calibrar para reproduzir throughput, fila e lead time; backtest e sensibilidade;
confrontar com piloto real. Se a fila muda de lugar, a melhoria local pode não
melhorar o sistema. Não transformar cenário em previsão garantida.

### Modelo 5 — trajetórias atípicas para investigação

Decisão: pequena lista de casos incomuns. Baseline P90/IQR/regras; depois avaliar
Isolation Forest. Medir alertas úteis revisados/semana e esforço de revisão.
Sem feedback humano não afirmar acurácia, fraude ou falha de funcionário.

### Protocolo obrigatório para todos

1. Fixar alvo, instante, população, desfechos e uso permitido.
2. Separar por tempo e projeto_id, sem projetos cruzando treino/teste.
3. No corte T, só features e rótulos já conhecidos em T; cadastro atualizado depois,
   próxima etapa, última etapa, duração e quantidade final de visitas são vazamento.
4. Ajustar encoder/imputação/limiares só no treino; teste final intocado.
5. Avaliar por origem/status/mix, com N e incerteza. Não usar MAPE com duração zero.
6. Superar baseline e definir com gestor erro tolerável/capacidade de alertas antes
   de ver resultado. Não declarar sucesso apenas com R²/AUC agregada.
7. Modo sombra antes de intervenção; piloto humano, guardrails e rollback.
8. Monitorar deriva, calibração, cobertura e utilidade; fallback para baseline.

Base conferida: 6.227 passagens elegíveis, 6.202 ViU2 e só 25 Globocorp. Pesquisa
histórica não comprova generalização ao fluxo novo. Começar com BI e regras úteis,
não prometer IA confiável na operação atual. Nenhum modelo homologado nesta entrega.

Ferramentas: Power BI/BigQuery para BI; Python, pandas/scikit-learn para regressão
e classificação; scikit-survival para sobrevivência; BigQuery ML como opção SQL.
Scoring diário no Cloud Run é evolução futura após contrato/aprovação, sem novo
serviço hoje. LLM pode narrar medidas verificadas, não calcular SLA nem inventar causas.

## 6. Como vender, operar e avaliar

Proposta: "reduzir imprevisibilidade e espera, preservando qualidade".
Rito semanal de 20 minutos: resultado → gargalo → três casos → hipótese → dono →
prazo → sucesso/guardrails. Ações ficam em ferramenta corporativa aprovada;
dashboard HTML não é aplicativo de writeback.

Demo fictícia: feedback tem 60% do tempo; revisar 10 casos e distinguir espera
externa de briefing incompleto; piloto de rodada consolidada/checklist; medir
P90 do ciclo, retornos por defeito, volume e idade dos abertos. Comparar mesmo mix.
Não chamar queda de tempo com mais recusas de sucesso. Benefícios: confiabilidade
de prazo, menos cobrança manual, priorização e melhoria testada. ROI exige custo/
benefício medidos; horas de permanência não viram horas de salário poupadas.

## 7. Plano quinta/sexta e critérios de entrega

Quinta 24/09: confirmar Scheduler + execução + publicação + corte; rodar diagnóstico
de ciclos; pactuar entrega/terminal/reabertura; montar modelo e executivo/gargalos.
Sexta 25/09: processo, projeto, confiança, testes de filtros e aceite com gestor.
Segunda 28/09: priorizar novas tabelas de briefing, motivo de revisão, entrega,
atribuição histórica e estado atual. Contrato antes da coleta/persistência.

Pendências de negócio para liberar ponta a ponta de entrega: marco exato de entrega,
trato de declinados/reaberturas, identidade de ciclo entre contas, metas, natureza
dos status e responsáveis históricos. Enquanto isso, os KPIs atuais permanecem
usáveis no seu escopo; novos KPIs ficam identificados como proposta/bloqueados.
Dashboard pronto = números reconciliados, população clara, ações definidas e
decisões sustentáveis. Aparência bonita sozinha não atende o objetivo.

## Referências técnicas

- [Modelo estrela Power BI](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema)
- [HTML Content: interatividade](https://html-content.com/docs/interactivity)
- [HTML Content: limitações](https://html-content.com/docs/limitations)
- [HTML Content Lite: sanitização](https://html-content.com/docs/sanitization)
- [Regressão quantílica](https://scikit-learn.org/stable/auto_examples/ensemble/plot_gradient_boosting_quantile.html)
- [Vazamento de dados](https://scikit-learn.org/stable/common_pitfalls.html)
- [Avaliação de sobrevivência](https://scikit-survival.readthedocs.io/en/stable/user_guide/evaluating-survival-models.html)
- [BigQuery ML: árvores](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-create-boosted-tree)
