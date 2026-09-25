# Tabelas, evidencias e ciclos continuos

## Estado em 25/09/2026

Producao v17 ainda usa exclusao integral por qualidade de trajetoria e regra
antiga de precificacao. Nao publicar novos KPIs como se essa regra ja tivesse
sido substituida. Motor live_cycles.py e contrato de monday_ciclos_orcamento
implementados localmente, com 18 testes especificos de motor/contrato/ensaio.
Worker oferece ensaio somente leitura; publicacao diaria permanece v17.
Impacto real, migracao do publicador, recuperacao e deploy ainda pendentes.
Procedimento: [ENSAIO_CICLOS_CONTINUOS.md](ENSAIO_CICLOS_CONTINUOS.md).

## Decisao de negocio atual (substitui proposta de so ciclos concluidos)

Primeiro status conhecido do projeto deve ser Entrada, considerando as duas
origens vinculadas. NULL anterior permitido se nao sobrepoe Entrada. Sem Entrada
nao entra na trajetoria principal. Projetos em Entrada ou elaboracao sao validos
em andamento, nao precisam chegar ao Feedback para aparecer na analise.

Operacao: Entrada e todas as etapas operacionais/revisoes mapeadas.
Entrada representa fila, nao horas efetivamente trabalhadas. Feedback fecha
entrega; retorno a trabalho inicia ciclo seguinte sem exigir outra Entrada.
Retornos internos, inclusive Entrada repetida, preservam tempo e evidencias.
Retorno Marca/Executivo e espera por terceiros; Standby e pausa separada.
Feedback e espera pelo retorno do orcamento. Nenhum desses tres compoe SLA
operacional. Encerrado/declinios interrompem; nao criam entrega ficticia.

Ambiente nao e chave de ciclo: identidade do projeto e preservada na migracao.
Uma lacuna nao pode ser preenchida automaticamente pela proxima observacao.
Tempo observado, estimativa e idade aberta ate corte sao naturezas diferentes.
Status desconhecido fica sinalizado. Mesmos trechos elegiveis para horas corridas
e uteis, calendario seg-sex 10-13/14-19, feriados BR PUBLIC e extras configurados.

## Uso por tabela atual

| Tabela | Pergunta / acao de gestao | Cuidado |
|---|---|---|
| monday_sla_orcamento | Onde as passagens observadas consomem tempo? Mediana/P90 por etapa para escolher gargalos a investigar. | Uma linha por passagem; populacao filtrada v17. Nao representa toda operacao nem novos ciclos ainda. |
| monday_fila_precificacao | Quais projetos selecionados so tem Entrada e ha quanto tempo aguardam? Priorizar triagem. | Uma linha por projeto; idade ate captura. Nao e toda fila do board. |
| monday_sla_baixa_qualidade_de_dado | Por que um projeto ficou fora? Priorizar correcoes e revisar evidencias. | Uma linha por projeto, varios motivos; nao somar motivos como projetos distintos. |
| monday_backlog_agenciamento_2026 | Como esta a carteira atual por status, marca, talento, tipo e responsaveis cadastrados? Distribuir demandas e achar campos ausentes. | Retrato diario; contagem de itens nao e automaticamente contagem de projetos. Nao mede historico de transicoes ou autoria passada. |
| monday_talentos_exclusivos | Como esta o cadastro de talentos/vinculos e responsaveis? Identificar ausencia de dono e apoiar segmentacao. | Associar ao backlog por vinculo validado; nao join aproximado por nome. Nao contem receita ou performance economica comprovada. |
| monday_sla_orcamento_viu2 | Auditar passagens historicas e recuperar trecho antigo do projeto. | Fonte congelada; nao somar diretamente com consolidada. |
| monday_sla_orcamento_globocorp | Auditar movimentos observados na origem atual. | Copia de item nao comprova inicio original do projeto. |
| monday_log_viu2 | Consultar evidencias brutas de mudancas. | Logs nao sao passagens; nao contar como ciclos/entregas. |

## Evidencias nos cinco exemplos reais recebidos

Identificadores e nomes de clientes ficam na consulta privada, nao neste guia.
Quatro exemplos: Entrada -> operacao/revisoes -> Feedback no historico ViU2,
seguido de Encerrado Globocorp; falta saida observada do Feedback. O trecho de
precificacao esta encadeado, mas a cronologia completa da migracao nao esta
comprovada. A regra v17 exclui o projeto inteiro, descartando tambem aquele trecho.

Quinto exemplo: Entrada -> operacao -> Entrada -> Revisao ViU2, seguido de
Declinado Internamente Globocorp, sem Feedback observado. Nao afirmar entrega,
nem calcular duracao completa da revisao. Falta de evidencia nao prova erro humano.

Nenhum dos cinco e exemplo comprovado de continuidade integral entre ambientes.
Encontrar identidade e achar todas as transicoes sao testes distintos.

## Analises depois de integrar a regra nova

- Primeira entrega: tempo operacional de Entrada ate primeiro Feedback.
- Revisoes/reenvios: quantidade de ciclos posteriores e duracao de cada um.
- Andamento: ciclo aberto, etapa, idade no corte, fila versus elaboracao.
- Terceiros: espera por informacoes, ocorrencias e esperas abertas.
- Feedback: espera apos envio do orcamento, separada da espera de briefing.
- Qualidade/cobertura: proporcao com evidencia utilizavel, estimada ou ausente.

Grain planejado de ciclos: projeto + passagem inicial do ciclo, chave estavel;
mesmo ciclo transita de aberto para entregue. Nao duas tabelas fisicas independentes
para abertos/fechados. Contrato de publicacao ainda precisa ser implementado.
Somar so categorias nao sobrepostas; numero de passagens nao e numero de projetos.
Sem metas acordadas, nao chamar P90 de atraso ou cumprimento de SLA contratual.

## Portoes antes da entrega

1. Quantificar casos na populacao atual incluindo os excluidos v17.
2. Reconciliar ciclos, trajetoria e qualidade sem perder evidencias/IDs.
3. Definir schema, validacao, journal, rollback e atualizacao diaria dos destinos.
4. Testar migracao, novas Entradas, reaberturas, lacunas, feriados e exclusoes.
5. Publicar com controle de concorrencia e conferir artefatos e BQ reais.

Alerta externo homologado para os tres destinatarios; nao bloqueia esses passos.
