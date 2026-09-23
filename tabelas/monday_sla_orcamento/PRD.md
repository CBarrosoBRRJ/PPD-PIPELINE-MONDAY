# SLA consolidado — contrato de análise v7 (candidato)

Status: v11/contrato v6 publicada; execução pipeline-monday-f9gbw e campos no BQ
confirmados pelo operador. Agenda reativada; próxima execução automática pendente
de evidência. Não repetir migrações antigas.

## Objetivo e população

Uma linha por passagem cronológica comprovada de projeto selecionado e mapeado
entre ViU2 e Globocorp, presente na Gold atual. Chave interval_id preservada;
não representa todos os projetos das origens. Não inventar continuidade entre contas.
Mesmas exclusões de título/Input e mesmos cálculos/expediente da v3.

## Campos novos (schema aditivo)

| Campo | Tipo/nulo | Uso |
|---|---|---|
| sla_etapa_horas_uteis | FLOAT, nullable | Medida exclusiva do KPI; copia duracao_horas_uteis só quando aprovada |
| classificacao_consumo | STRING, required | Papel desta passagem na análise |
| motivos_inelegibilidade_kpi_json | STRING, required | Lista JSON dos motivos; [] quando elegível |
| versao_regra_kpi | STRING, required | Política kpi-etapa-origem-v1 |

Classes: aprovado_kpi_etapa, encerramento_observado, sem_saida_observada,
evidencia_insuficiente. Classificação é da passagem, não situação atual do projeto.
Terminal conhecido tem prioridade como encerramento observado, sem aprovar cadeia
completa. Sem saída não prova abandono nem que esteja em andamento atualmente.
Detalhes de qualidade continuam nos motivos e nos campos de origem existentes.

## Consumo

AVG(sla_etapa_horas_uteis) por ambiente/status dispensa os três filtros de elegibilidade.
COUNT(sla_etapa_horas_uteis) é o número de passagens no KPI. COUNT(*) inclui outras
situações; projetos com etapa elegível exigem COUNT DISTINCT condicionado ao campo
não nulo. Nunca transformar nulo em zero. Zero útil observado continua sendo válido.
Usar sql/kpi_consumo.sql. Filtragem por período, se necessária, usa saída da passagem.
Não somar ambientes como ciclo completo, inferir produtividade pessoal ou aplicar
metas de atraso não definidas. Média descreve concluídas, não fila ou esforço.

## Garantias e manutenção

Mantém todas as 9.648 linhas da base auditada, IDs, datas, flags v3 e durações originais.
Acrescenta quatro campos; só versao_contrato muda nos existentes.
Construção e validação recalculam projeção em Python em toda execução diária.
Campo de KPI indevido, classificação divergente ou motivos/versionamento incorretos
bloqueiam lote. Não corrigir tabela pontualmente com UPDATE.
Coordenador publica schema explícito com WRITE_TRUNCATE atômico, sem tabela extra.
Leitura v2/v3/v4/v5/v6 existe para reconciliação de publicação anterior; novo candidato exige v7.
Atualizar gerador de contrato/DDL, testes, guias e migração antes de mudar semântica.

## Validação preventiva por projeto

Auditoria local adicional em [AUDITORIA_TRAJETORIA.md](docs/AUDITORIA_TRAJETORIA.md).
Confere sequência, cronologia e identidade nativa em todo lote; corrupção
estrutural bloqueia a publicação. Lacunas de evidência geram contagens no relatório
operacional sem inventar datas, remover passagens válidas ou aprovar SLA total.
Evolução v5 acrescenta cinco campos obrigatórios, sem mudar os dados anteriores
além de versao_contrato: quantidade_passagens_projeto (INT64), qualidade_trajetoria
(STRING), limitacoes_trajetoria_json (STRING), eh_ultima_etapa_observada (BOOL) e
versao_regra_trajetoria (STRING). A projeção é recalculada antes da publicação e na
reconciliação; divergência bloqueia carga. Não cria tabelas adicionais.

Grão continua uma passagem. Contagem e qualidade do projeto repetem-se nas suas
linhas: usar eh_ultima_etapa_observada para contar projetos, nunca somar a contagem
repetida. Última etapa observada não é garantia do estado atual. Histórico com
limitações não invalida automaticamente as etapas com KPI comprovado. Sequência
sem lacunas detectadas não equivale a completude vitalícia homologada.
Proteção v5 confirmada no GCP pela execução pipeline-monday-rbldd.

## Hipótese analítica opcional v6

Autorizada pelo usuário: estimar a saída da última passagem ViU2 sem saída usando
a próxima entrada Globocorp do mesmo projeto selecionado no mapa. Somente origem
ViU2 -> Globocorp; não aplicar a lacunas internas ou à última passagem sem sucessora.
Não altera os campos observados, as limitações, continuidade_validada ou elegibilidade.
Não promove a identidade selecionada por política a migração comprovada.

Oito campos adicionais: saida_estimada_utc (TIMESTAMP nullable),
saida_estimada_local (DATETIME nullable), duracao_estimada_horas e
duracao_estimada_horas_uteis (FLOAT nullable), metodo_estimativa (STRING required),
interval_id_referencia_estimativa (STRING nullable), versao_regra_estimativa
(STRING required), versao_calendario_estimativa (STRING nullable).
Método aplicável: estimada_pela_proxima_etapa_entre_ambientes; demais nao_aplicavel.

Hipótese explícita de permanência no mesmo status até a próxima observação, sem
mudanças intermediárias. Pode superestimar permanência real. Não é KPI oficial,
verdade histórica, comprovação de abandono ou alvo automaticamente válido para ML.
Horas úteis usam o calendário versionado padrão da consolidação. Saída local é
derivada da UTC em São Paulo; horas arredondadas a 3 casas, zero útil legítimo.

Bloqueia estimativa quando houver sobreposição no projeto, saída observada,
status terminal/desconhecido, mesmo status ou origem, identidade fora da política,
falta de próxima passagem, data não crescente ou além do corte.
Toda execução reconstrói e revalida os oito campos antes de publicar. Se chegar
saída observada, a estimativa deixa de ser aplicável. Divergência bloqueia o lote.
Métrica oficial sla_etapa_horas_uteis permanece sem estimativas. Não há tabela nova.

## Duração unificada v7 — decisão posterior do usuário

Release v12 candidata, ainda não implantada. O usuário solicitou um par único de
medidas para análise com valores observados e estimados. Acrescentar:
duracao_analise_horas e duracao_analise_horas_uteis (FLOAT nullable),
origem_duracao_analise e versao_regra_duracao_analise (STRING required).
Grão permanece passagem. Observação validada tem prioridade; estimativa permitida
é usada somente sem saída observada. Resto é indisponivel/NULL, nunca zero sintético.
Terminal ou classificação desconhecida não recebe duração unificada.

Origem: observada_validada / estimada / indisponivel. Versionamento duracao-analise-v1.
Não promove métricas reprovadas existentes na linhagem. Recalcula projeção em toda
execução; divergência bloqueia publicação. Campos anteriores, horas, calendário,
IDs e flags preservados. v7 pode reconciliar snapshot v6 para substituição atômica.

Calendário permanece seg-sex 10–13 e 14–19 America/Sao_Paulo, BR PUBLIC e extras
configurados. Carnaval e Corpus Christi não são excluídos automaticamente.
Não há arredondamento novo: usa as horas já validadas a três casas decimais.
Para consumo unificado usar sql/duracao_unificada.sql e sempre informar quantas
passagens são estimadas. sla_etapa_horas_uteis continua o KPI estritamente observado;
o indicador unificado inclui hipóteses e não aprova SLA total entre ambientes/ML.
