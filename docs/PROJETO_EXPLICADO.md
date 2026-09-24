# Pipeline Monday — o que faz e como consumir

Estado: upgrade v13/contrato v8 candidato. A última produção confirmada é v12/v7.
GitHub atualizado não significa imagem implantada; a entrega exige recibo do GCP.

## Objetivo

Reduzir o tempo de precificação: entender quanto demoramos entre Entrada e primeiro
Aguardando Feedback e onde o tempo ficou concentrado. Cadastro atual, trajetória
histórica e KPI são informações diferentes e permanecem identificadas.

## Produtos

| Produto | Conteúdo e atualização |
|---|---|
| monday_backlog_agenciamento_2026 | Cadastro diário dos itens ativos retornados do board 18429499488, todos os grupos, sem filtros do SLA |
| monday_talentos_exclusivos | Cadastro diário do board 18429499631, inclusive grupos não exclusivos e finalizados |
| monday_sla_orcamento_globocorp | Passagens históricas disponíveis da origem atual, fechamento D+1 |
| monday_sla_orcamento_viu2 / monday_log_viu2 | Histórico congelado preservado; não consulta a conta antiga diariamente |
| monday_sla_orcamento | Passagens dos projetos selecionados/mapeados, métricas de etapa, precificação e cadastro atual identificado |

As duas primeiras são novas e ainda exigem primeira publicação/homologação. O nome
2026 não aplica um filtro oculto de ano. Cadastro de talentos não prova equivalência
com dropdowns de outros boards: não há join por semelhança de nome.

## Rotina diária candidata

Agenda existente às 06h America/Sao_Paulo chama o coordenador. Ele coleta backlog,
talentos e SLA da origem atual; produtos independentes continuam após falha de
outro. A consolidada só roda com SLA e backlog publicados/verificados. Captura
de cadastro reflete o momento da coleta; não é o corte D+1 dos eventos do SLA.

Cada snapshot percorre todas as páginas, confere IDs únicos, colunas e tipos,
contagem e estabilidade do schema. Guarda a evidência selecionada no GCS privado.
Após validar, grava journal e NDJSON; o load BQ substitui a tabela atomicamente.
Confere todas as linhas por fingerprint antes de promover o ponteiro ativo. Uma
falha não é interpretada como exclusão. Resultado incerto é retomado pelo mesmo
job ID; locks não expiram automaticamente.

Itens que deixam o escopo da coleta deixam o snapshot no próximo sucesso; isso
pode representar exclusão, arquivamento ou movimentação. O snapshot não distingue
esses motivos. API items_page não enumera arquivados/lixeira. Subitems não são
incluídos automaticamente. Board vazio bloqueia substituição até revisão.
Fonte: [items_page](https://developer.monday.com/api-reference/reference/items-page).

## Regras de tempo

Entrada inicia tentativa; elaboração e revisão contam; Standby e Retorno
Marca/Executivo pausam. Primeiro Aguardando Feedback fecha a precificação.
Encerrado/declinados antes dele encerram sem entrega. Nova Entrada reinicia
tentativa; revisões posteriores ao feedback não prolongam a entrega anterior.

- Corridas: somar intervalos contáveis, excluindo pausas.
- Úteis: os mesmos intervalos, seg-sex 10–13/14–19, São Paulo, BR PUBLIC e extras.
- Totais aparecem somente na linha da entrega aprovada, evitando multiplicação.
- Lacuna, status desconhecido, calendário divergente ou evidência insuficiente:
  KPI NULL, com motivo. Zero é um resultado observado, nunca substituto de NULL.
- Não ligar contas distintas automaticamente. Estimativa não entra no KPI observado.
- Status novo não é aprovado por conter a palavra elaboração; o mapeamento é explícito.

Mantêm-se as exclusões específicas do SLA existentes (títulos, Input e identidade).
Elas não são aplicadas aos novos cadastros completos. A consolidada não representa
automaticamente todos os 4.847 itens vistos no board na inspeção de 24/09.

## Dashboard útil para gestão

1. Entregas: N de ciclos aprovados, P50/P90 em corridas e úteis, cobertura e período.
2. Diagnóstico: contribuições por etapa, pausas, exemplos de trajetórias e retornos.
3. Backlog: situação atual por grupo/status, responsáveis e tipos de demanda.
4. Confiança: última captura, corte do SLA, estimativas, ciclos incompletos e motivos.

Comparar mesmo ambiente/tipo de demanda. Tempo em status não mede esforço nem culpa
individual. Responsáveis e marca com prefixo cadastro_atual_ são atuais, não autores
históricos. Não usar esse cadastro futuro como feature de previsão retrospectiva.
ML é etapa posterior: primeiro baseline por tipo/etapa, depois validação temporal
de previsão de prazo/risco, com dados disponíveis no instante da previsão. Não há
modelo treinado ou indicador de ganho causal homologado neste pacote.

## Falhas e alertas

Logs estruturados identificam produto com falha; coordenador termina com erro se
algum produto falhar/bloquear. Há adaptador opcional de e-mail STARTTLS para endpoint
corporativo explicitamente configurado. Sem configuração, registra not_configured;
não afirma que e-mail chegou. Credenciais expostas precisam de rotação, via Secret
Manager; não são copiadas para .env/Git. Canal externo ainda requer homologação.

## O que falta para dizer “entregue”

Build no GCP, digest fixado, plano de migração corrente revisado, migração CAS,
execução diária real dos quatro produtos, schema/conteúdo reconciliados e agenda
retomada. Verificar qualidade/cobertura real da precificação e recebimento de alerta.
Somente então comparar commit, inventário do ZIP e digest implantado. Testes locais
e CI não substituem essas evidências, nem garantem ausência absoluta de erros.
