# Recorte de precificação com os status atuais

Decisão de negócio confirmada em 24/09/2026. Não aguardar a futura reunião de
redesenho dos status. Este documento define a próxima implementação; não é
recibo de alteração do contrato publicado `sla-consolidado-analise-v7`.

## Pergunta prioritária

Quanto tempo levamos da Entrada até o primeiro Aguardando Feedback, descontando
as pausas acordadas? Onde esse tempo ficou concentrado dentro da precificação?

| Status atual | Papel nesta medição |
|---|---|
| Entrada | Início comprovado do ciclo; sua permanência conta |
| Elaboração e revisão, incluindo suas especialidades | Permanência conta |
| Standby | Pausa; permanência excluída de ambas as medidas |
| Em elaboração - Retorno Marca/Executivo | Pausa por informação; excluída de ambas |
| Aguardando Feedback | Sua primeira entrada encerra a precificação; sua permanência não entra |
| Encerrado, Declinado Internamente, Declinado pelo Mercado | Se anteriores à entrega, encerram o ciclo sem entrega comprovada |
| Status desconhecido ou sem classificação | Pendência; não aprovar automaticamente a duração do ciclo |

As famílias de elaboração/revisão acima descrevem a intenção de negócio, não
autorizam aceitar automaticamente qualquer novo rótulo por prefixo. A implementação
deve enumerar os status conhecidos e tratar Retorno Marca/Executivo como exceção.

## Dois relógios, as mesmas etapas

- **Horas corridas de precificação:** soma dos intervalos contáveis dentro da
  janela Entrada → primeiro Aguardando Feedback, sem as pausas acima.
- **Horas úteis de precificação:** os mesmos intervalos, restritos a segunda a
  sexta, 10–13h e 14–19h, America/Sao_Paulo, excluindo feriados BR PUBLIC e extras
  configurados. Reusar o calendário Python do pipeline.
- **Janela total e pausas:** medidas auxiliares para explicar a diferença entre
  o prazo decorrido no calendário e o tempo atribuído à precificação.

Não chamar as medidas apenas de bruto/líquido. Horas úteis não são esforço
efetivamente trabalhado. Revisão conta; não deve ser confundida com pausa.
Lacuna não é pausa nem zero. Estimativas permanecem separadas de fatos observados.
Sem Entrada comprovada, fim comprovado ou decomposição suficiente, sinalizar a
limitação em vez de inventar duração. Não somar intervalos sobrepostos.

## Entrega incremental

1. **Usar agora:** diagnóstico de permanência observada por etapa e ambiente,
   trajetória por projeto e cobertura de evidências. Os campos existentes de
   duração por passagem não são ainda o novo SLA de precificação.
2. **Implementar e validar:** delimitação dos ciclos, exclusão das pausas, horas
   corridas/úteis e decomposição por etapa. Não obter o ciclo apenas filtrando
   nomes de status: isso incluiria revisões posteriores ao primeiro feedback.
3. **Liberar o cartão de precificação:** somente após reconciliar exemplos e
   publicar o novo contrato. Cada ciclo conta uma vez, não uma vez por passagem.
4. **Depois da reunião:** revisar o mapeamento e sua vigência sem reclassificar
   silenciosamente o histórico. Retorno do cliente e jornada de venda ficam como
   análises posteriores, não como bloqueio desta primeira entrega.

No dashboard, priorizar P50/P90 dos ciclos elegíveis, quantidade de entregas,
cobertura, concentração de tempo por etapa e pausas. Até a etapa 3, identificar
claramente os gráficos disponíveis como **permanência por etapa**, não prazo de
entrega. Não atribuir todo o histórico à pessoa atualmente cadastrada no item.

## Casos mínimos de aceite da próxima implementação

- Entrada → elaboração → revisão → feedback: revisão incluída, feedback excluído.
- Pausa → retomada dentro do ciclo: pausa excluída dos dois relógios.
- Retorno Marca/Executivo: mesma exclusão, com motivo preservado.
- Declínio/encerramento antes do feedback: sem entrega, fora do percentil de entregas.
- Etapas após primeiro feedback: fora deste primeiro ciclo de precificação.
- Fim de semana, almoço e feriado: alteram horas úteis, não horas corridas contáveis.
- Lacuna, estimativa ou fronteira entre contas sem continuidade comprovada:
  não promovidas a ciclo observado aprovado.

Novas tabelas de backlog e talentos continuam no escopo do upgrade, coletando
todos os itens dos boards com status/grupo. Não dependem da mudança futura dos
status; também não estão publicadas por causa deste documento.
