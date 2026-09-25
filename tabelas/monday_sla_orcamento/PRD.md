# SLA consolidado — contrato de consumo

## Candidato v18 — ciclos continuos (ainda nao implantado)

Ver docs/ENTREGA_V18_CICLOS.md e docs/VALIDACAO_E_ANALISE_CICLOS_V18.md na raiz.
Publicacao de quatro tabelas com journal separado e transacao unica. Colunas
aditivas sla_* e ciclo_id; contrato fisico docs/schema_ciclos_v18.json. Mantem
linhagem v9, cujos campos de precificacao sao legados e nao medem ciclos novos.
Nova tabela monday_ciclos_orcamento e referencia de totais e KPI de entrega.
Fila e subconjunto da principal; qualidade diagnostica pode coexistir com SLA.
Esta decisao substitui exclusao integral v17 exceto falta de Entrada inicial
ou prefixo nulo sobreposto. Evidencias/cadastros/filtros de escopo preservados.

## Candidato v17 — separação de destinos (não implantado)

Schema v9 preservado; população muda somente após inicialização explícita do
journal destinos-projeto-v1. Worker reconstroi toda a população anterior das fontes
verificadas e só então separa por projeto, permitindo reinclusão após correção.
SLA recebe sequência aceita começando em Entrada; fila recebe Entrada isolada
confirmada no cadastro atual; baixa qualidade recebe projeto inteiro com motivos.
Entrada em outro dia que criação é permitida; fluxo direto observado até Feedback
também. Prefixos nulos são preservados como evidência sem KPI, não etapas inventadas.
Projetos em andamento com sequência aceita não são automaticamente entregas.
Detalhes, recuperação e limitação da população: docs/SEPARACAO_SLA_FILA_QUALIDADE.md
na raiz. Não inclui automaticamente itens sem mapa ou fora dos filtros anteriores.

## Candidato v9 — talento atual unificado (ainda não implantado)

### Revisão v15: escopo obrigatório de talento

Substitui o pacote v14 ainda não implantado. Política `talento-cadastro-unico-v1`
na consolidada: excluir TODAS as passagens do projeto nas duas origens quando
o cadastro atual verificado tiver ambas as colunas preenchidas (mesmo se nomes
iguais), nenhuma preenchida, mais de um exclusivo ou a palavra Squad em qualquer
uma delas (independente de caixa, incluindo Squad de Talentos).
Espaços e entradas vazias não contam como preenchimento. Não inferir pessoas
separando texto livre. Motivos e IDs dos projetos excluídos ficam no report.json
privado da publicação, com contagens por origem. Não apagar/modificar fontes nem
filtrar as tabelas completas de backlog/talentos. Correção na origem pode reincluir
na próxima execução se os demais critérios forem atendidos. Ausência técnica de
cadastro/schema ou JSON malformado bloqueia a carga; não equivale a cadastro vazio.
Revalidar a política no lote final para impedir publicação indevida. Leitura de v8
continua preservada para reconciliação; agenda e migração seguem controladas.
Redução de contagens é esperada, mas só pode ser quantificada na execução real.

Estado mais recente: release v13/v8 executada conforme docs/ESTADO_GCP_2026_09_24.md
na raiz; homologação independente e retomada da agenda pendentes. As seções
cronológicas abaixo não substituem esse recibo.

Grão e interval_id preservados. Quatro campos aditivos: talento_nome_atual
(STRING nullable), eh_interveniencia (BOOL nullable), talentos_atuais_json
(STRING nullable) e situacao_talento_atual (STRING required). Origem exclusiva:
cadastro atual verificado do backlog. Não altera talento_nome histórico.
Um único rótulo exclusivo recebe FALSE; um único texto de Interveniência sem
marcadores de multiplicidade recebe TRUE. Campo descreve origem, não contrato
ou identidade individual certificada. Múltiplos exclusivos, ambas as origens
ou texto com separadores geram nome/flag escalares NULL, com situação explícita.
Lista preserva nomes, origem e flag por entrada; texto livre não é separado nem
unido por similaridade. Campos originais permanecem. Grão não é expandido.
JSON inválido bloqueia lote; projeção é recalculada na construção e validação.
Ausência de cadastro fica explícita e não significa FALSE. Consumers: análise
por origem do talento atual; não autoria/vínculo histórico. Migração v8→v9 exige
imagem por digest, agenda pausada, plano atual e verificação da publicação.

## Candidato local v8 — precificação (NÃO implantado)

O código candidato acrescenta o cálculo Entrada → primeiro Aguardando Feedback
na mesma origem. Contrato `sla-consolidado-precificacao-v8`; produção permanece
v7 até migração explícita, imagem validada e reconciliação. Não executar daily
com candidato v8 sobre controle v7. Enriquecimento cadastro_atual_ agora incluído
no candidato, dependente do snapshot diário de backlog verificado. Origem/data
explícitas: não substitui campos históricos nem comprova autoria passada.

Grão e chave permanecem passagem/interval_id. `ciclo_precificacao_id` identifica
a Entrada da tentativa; totais `precificacao_horas_corridas/horas_uteis`, pausas
e janela aparecem somente na linha da entrega aprovada. Filtrar
`entrega_precificacao_observada` para percentis e contagem de entregas.
Contribuições por etapa aparecem apenas nas etapas contáveis de ciclos aprovados.
Revisões contam; Standby e Retorno Marca/Executivo não contam em nenhum relógio.
Calendário segue o existente. Fechamento antes do feedback não é entrega.

Situação e motivos repetem-se nas passagens do ciclo: não somar como número de
ciclos. Nova Entrada reinicia tentativa; revisão posterior ao primeiro feedback
não é incluída sem nova Entrada. Origem, rótulo, calendário ou cadeia sem evidência
bloqueiam KPI; estimativas não alimentam estes campos. Essa regra não homologa
continuidade entre contas. Campos são recalculados na construção e validação;
divergência bloqueia publicação. Schema aditivo com strings/bool obrigatórios
para regra/papel/situação/motivos/flag; IDs, datas e durações são nullable.

Consumidores: painel de precificação e diagnóstico de etapas, não produtividade
individual. Ver `docs/RECORTE_PRECIFICACAO_ATUAL.md` na raiz. Migração/deploy e
reconciliação de dados reais ainda pendentes; não confundir teste sintético com
homologação da população.

Status: v12/contrato v7 publicada; execução pipeline-monday-jdc47 e campos no BQ
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

Release v12 implantada e conferida pelo operador em 23/09/2026 (ver recibo na documentação de entrega). O usuário solicitou um par único de
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
