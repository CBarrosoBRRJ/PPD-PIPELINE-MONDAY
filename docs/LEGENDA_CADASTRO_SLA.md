# Legenda de consumo — cadastro e SLA

## Onde consultar

A tabela final e `viu_agenciamento.monday_sla_orcamento`. Cada linha representa
uma passagem por status, nao um projeto inteiro nem uma pessoa.

Use `tabelas/monday_sla_orcamento/sql/cadastro_analitico.sql` no editor SQL do
DBeaver ou BigQuery. Ela apresenta aliases claros, sem criar tabela/view nem
alterar o schema publicado. O limite de 100 linhas serve para inspecao, nao para
alimentar o dashboard inteiro. Para inspecionar um projeto, filtre por projeto_id
antes do ORDER BY. item_id sozinho pode mostrar apenas uma das origens.

## Cadastro atual: campos ja previstos no contrato v8

| Coluna fisica na consolidada | Significado |
| --- | --- |
| cadastro_atual_marca | Marca no cadastro atual do backlog |
| cadastro_atual_talentos_exclusivos_json | Lista dos nomes na coluna Talentos Exclusivos |
| cadastro_atual_interveniencia | Texto original da coluna Interveniencia; nao separar por pontuacao sem regra validada |
| cadastro_atual_orcamento_json | Responsaveis atuais de Orcamento |
| cadastro_atual_talent_manager_json | Talent Managers atuais |
| cadastro_atual_gp_json | Responsaveis atuais da coluna GP |
| cadastro_atual_conteudo_json | Responsaveis atuais de Conteudo |
| cadastro_atual_producao_json | Responsaveis atuais de Producao |
| cadastro_atual_audiencia_json | Responsaveis atuais de Audiencia |
| cadastro_atual_tipo_projeto | Tipo de Projeto atual |
| cadastro_atual_tipo_input | Tipo de Input atual |
| cadastro_atual_tipo_output | Tipo de Output atual |
| cadastro_atual_capturado_em | Momento da captura do cadastro, nao da mudanca de status |
| cadastro_atual_origem_json | Evidencia de origem do cadastro usado no enriquecimento |

Os campos de pessoas sao listas JSON com ID, tipo (pessoa/equipe) e nome quando
disponivel. Preservar IDs: nomes iguais nao identificam necessariamente a mesma pessoa.
Vazio nao significa ausencia de trabalho; significa ausencia de informacao na captura.

O cadastro atual pode aparecer em passagens historicas ViU2 mediante a
correspondencia de projeto existente. Isso NAO comprova quem atuou naquela epoca.
Nao usar responsavel atual como autoria historica nem como medida de produtividade individual.

## Talentos: nao confundir as colunas

### Candidato v9: nome unificado e flag (ainda nao publicado)

| Campo fisico novo | Significado |
| --- | --- |
| talento_nome_atual | Rotulo unico do cadastro atual quando nao ambiguo; nao altera talento_nome preexistente |
| eh_interveniencia | TRUE: origem Interveniencia; FALSE: origem Talentos Exclusivos; NULL: ausencia/ambiguidade |
| talentos_atuais_json | Lista de entradas com nome, eh_interveniencia, origem e texto_nao_estruturado |
| situacao_talento_atual | sem_cadastro, nao_informado, rotulo_unico_na_origem, multiplos_exclusivos, ambas_origens ou interveniencia_requer_revisao |

Texto de Interveniencia com separadores nao vira uma pessoa artificial: fica na
lista como texto livre, com escalares NULL. Ausencia de separadores tambem nao
certifica identidade de pessoa. Duas origens com nome igual nao sao mescladas.
Nenhuma dessas regras amplia a populacao selecionada para SLA ou remove filtros.
Consulta cadastro_analitico.sql agora requer v9; auditoria_cadastro_atual.sql
continua compativel com v8. Usar auditoria_talentos.sql depois da migracao v9.

`talento_nome` e um campo preexistente derivado do tratamento da origem; nao e
uma concatenacao geral das duas colunas atuais. O tratamento da origem pode
excluir casos ambiguos/multiplos segundo o escopo de SLA existente. A v13 nao
ampliou esse escopo para todos os itens do backlog.

A consulta cria `origem_talentos_cadastro_atual`:

- `exclusivos`: apenas a lista de Talentos Exclusivos esta preenchida;
- `interveniencia`: apenas o texto de Interveniencia esta preenchido;
- `ambos`: as duas colunas estao preenchidas;
- `nao_informado`: nenhuma tem valor util.

Essa classificacao indica a coluna de origem, nao certifica vinculo contratual nem
aprova identidade de talentos. Os dois valores continuam separados; nao ha novo join
por nome com a tabela de talentos. Nao duplicar passagens para cada talento/pessoa:
isso multiplica duracoes. No Power BI, listas exigem pontes e medidas que preservem
a unicidade da passagem/projeto.

## Medidas e datas

| Campo | Uso |
| --- | --- |
| projeto_id | Identificador consolidado para acompanhar a trajetoria |
| interval_id | Chave da passagem; controle de duplicidade |
| ordem_etapa | Ordem observada no projeto; nao garante ausencia de lacunas |
| saida_status_local | Saida observada; NULL nao deve virar zero |
| saida_estimada_local | Saida inferida, separada da observada |
| duracao_analise_horas | Horas corridas para analise, observadas validadas ou estimadas |
| duracao_analise_horas_uteis | Horas no calendario util, observadas validadas ou estimadas |
| origem_duracao_analise | Proveniencia da duracao: observada_validada, estimada ou indisponivel |
| sla_etapa_horas_uteis | Medida por etapa estritamente observada e elegivel |
| precificacao_horas_corridas | Tempo elegivel do ciclo Entrada ate Feedback, descontadas pausas previstas |
| precificacao_horas_uteis | Mesmo ciclo elegivel dentro do calendario util |
| entrega_precificacao_observada | Marca a linha de entrega; totais do ciclo nao devem se repetir nas demais |
| situacao_ciclo_precificacao | Situacao de entrega, abertura ou insuficiencia de evidencias do ciclo |

Calendario vigente: America/Sao_Paulo, segunda a sexta, 10h–13h e 14h–19h,
excluindo feriados BR PUBLIC e extras configurados. Revisoes contam; Standby e
Retorno Marca/Executivo pausam as duas medidas de precificacao. Encerramento/declinio
antes de Feedback nao prova entrega. Ciclos entre contas sem continuidade comprovada
nao devem ser transformados em KPI observado.

## Evidencias e limites desta revisao

Operador informou sucesso da execucao `pipeline-monday-2h8lf`:
backlog 4.860 linhas, talentos 41, consolidada 9.672 passagens / 2.209 projetos;
SLA Globocorp com publicacao anterior verificada. Rotina entre os timestamps de
orquestracao: aproximadamente 4min48s; nao inclui todo o provisionamento.

Os 12 atributos estao presentes no codigo de enriquecimento. A consulta
`tabelas/monday_sla_orcamento/sql/auditoria_cadastro_atual.sql` compara todos com
o backlog publicado; resultado real ainda pendente. Capturas diferentes podem
indicar publicacoes em momentos diferentes, nao necessariamente erro de mapeamento.

Aliases e legenda sao melhorias locais de consumo; nao sao renomeacao fisica em
GCP. Renomeacao exige versionamento do contrato, atualizacao do publicador,
testes e migracao de consumidores. Agenda permanece pendente de retomada apos
validacoes; alerta externo ainda nao homologado. Nao declarar entrega integral.
