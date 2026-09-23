# Estado confirmado pelo operador — 23/09/2026

Este recibo prevalece sobre previsões e estados anteriores de implantação.

## Recibo v12 — produção atual

Implantação e conferência BQ pelo operador registradas em
ENTREGA_V12_DURACAO_UNIFICADA.md. Imagem por digest
33263084d9f61172bf13b509c6df86ac195a3bff369c2d346c5d49d705dc6286;
execução pipeline-monday-jdc47 concluída. Contrato sla-consolidado-analise-v7,
9.648 linhas: 6.227 observadas validadas, 191 estimadas, 3.230 indisponíveis.
Ambas as durações unificadas com zero divergências na consulta sem cache.
Scheduler ENABLED às 06h America/Sao_Paulo; próxima execução automática pendente.
Não repetir migração. GitHub ainda não sincronizado/comprovado nesta entrega.

## Recibo v11 — histórico, substituído pela v12

Fonte: saídas do Cloud Shell e consulta DBeaver fornecidas pelo operador.
Imagem por digest:
94debc58d1f5eb702abef7489a4f9b6a57500623abe6ce30fe0059474c7f7d3b.
Pacote v11 SHA256 b3d76cf4c003bb6dd6e561e053aa6cab6a563638b088b7cda80e708229cc0a28.
Migração control-only confirmada; geração retornada 1790201161032266 pertence
ao recibo da migração, NÃO à publicação atual.
Execução pipeline-monday-f9gbw: consolidated_publication_confirmed em
2026-09-23T22:09:47.776486Z; orchestration_end success, publication_verified=true.
Corte 2026-09-23T03:00:00Z. BQ confirmou sla-consolidado-estimativas-v6,
9.648 passagens, 2.209 projetos, 6.227 valores de KPI, 191 estimativas e zero
estimativas indevidas na consulta executada. Exemplo ABRALE conferido no DBeaver.
Scheduler retomado pelo operador e confirmado ENABLED, 0 6 * * *, America/Sao_Paulo.
Próxima execução automática da v11 ainda NÃO observada. Não confundir esta execução
manual bem-sucedida com comprovação do próximo disparo automático.

KPI liberado: permanência de etapas elegíveis por ambiente/status, medida
sla_etapa_horas_uteis. Estimativas não pertencem ao KPI oficial. Não homologados:
SLA total entre ambientes, completude vitalícia e uso genérico para ML.
Código consolidado usa arquivos ViU2 congelados no GCS, não acesso à conta antiga.
Preservar arquivos históricos, contexto, mapa e controles; Globocorp segue necessário.
Não excluir recursos compartilhados; Terraform legado permanece pendente de reconciliação.

As seções abaixo são histórico dos recibos, não orientação para repetir migrações.

## Recibo v8 anterior

Imagem ce386dfef2accd87f2396b0659d05437366ea296f1427b0b738e6b77b944baa1;
migração v3 confirmada (geração no momento 1790196192066533, não assumir atual).
Execução pipeline-monday-c8hfd: publication_verified=true às 20:48:01Z,
9.648 passagens/2.209 projetos, corte 2026-09-23T03:00:00Z.
Consulta BQ confirmou contrato sla-consolidado-etapa-v3: 6.202 elegíveis ViU2
(2.081 projetos), 25 Globocorp (13 projetos), zero elegíveis inválidas no controle
consultado. 3.421 não elegíveis; continuidade global false. Origem skipped verificada.
Scheduler retomado pelo operador: ENABLED, 0 6 * * *, America/Sao_Paulo.
KPI liberado somente para etapa concluída, por origem, população selecionada,
com filtro de elegibilidade v3. Sem total global/metas de atraso.

Usuário aprovou campo de consumo exclusivo do KPI, classificação e motivos,
preservando abertas/terminais. V9/contrato v4 implementado localmente, não implantado:
quatro campos aditivos, sem mudar durações/IDs/população/elegibilidade da v3.
Ver ENTREGA_V9_CONSUMO.md e tabelas/monday_sla_orcamento/PRD.md.
Não executar migrações v7/v8 novamente nem desativar a agenda até etapa operacional.

## Recibo v7 posterior — prevalece sobre v6 e candidato abaixo

Operador confirmou imagem v7 por digest
881c2f44d802883b2a3dfb5099bf65ce22677babb36fa74316a0e26b19de969a.
Migração historical-labels-v2: applied_full_content_verified, 14.761 linhas,
job viu2_labels_v2_0a8016b8dd633fb1e94bc5b7f27c38f3. Controle consolidado migrado
na geração 1790193946151881 para history_sha d0aab3fdb25cb1f3746ee0f1c6db37c419e255034b6ce9786ff3e6d84e78af1e.
Essa geração é recibo da migração, não assumir atual após reconstrução.
Execução pipeline-monday-8qbwb confirmou publicação consolidada às 20:12:16Z:
9.648 passagens, 2.209 projetos, corte 2026-09-23T03:00:00Z, orquestração success.
Consulta BQ posterior confirmou 32 sem classificação e 9.648 validações pendentes.
Scheduler retomado e conferido ENABLED, 0 6 * * *, America/Sao_Paulo.
Globocorp skipped com publication_verified=true não foi falha.
Não repetir migração v7. Nenhuma sincronização GitHub confirmada.

Usuário aceitou avançar no KPI de etapa em horas úteis separado por ambiente,
sem liberar total entre contas. Política candidata local em kpi_etapa.py;
integrada localmente ao contrato v3, mas não implantada. Ver HOMOLOGACAO_KPI_ETAPA.md
e ENTREGA_V8_KPI_ETAPA.md. Snapshot ativo v7 recebido e reconciliado pelo hash
6c33244f4fff85a9f5ebd0e09685aed8a6bf746eb0f5d8df92e7b91363447987.
Diferença com reconstrução: somente representação de datas em registro_origem_json,
217 linhas; zero diferenças materiais. 6.227 candidatas (6.202 ViU2 / 25 Globocorp).
Não alterar contrato ativo antes de imagem nova em plan e agenda pausada.

## Candidato local posterior (não implantado)

Recuperação de rótulos históricos `historical-labels-v2` implementada no
enriquecimento viu2, com fallback restrito ao previous_value da saída comprovada.
Ver RECUPERACAO_ROTULOS_HISTORICOS.md. Não modifica a v6 já implantada nem
comprova igualdade com GitHub; reconstrução histórica e publicação pendentes.

Auditoria BQ informada pelo operador: 9.648 passagens/2.209 projetos; zero chaves
duplicadas, ausência de entrada/ordem, saídas invertidas, durações negativas,
horas úteis excedentes e terminais inválidos nos controles consultados. Títulos
proibidos/PACOTE e títulos vazios zerados nas três tabelas. Input ainda pendente
de auditoria contra cadastro. Todas as linhas seguem não aprovadas para comparação.
Dos 37 rótulos desconhecidos: 11 possuem nome no evento exato de saída, dez têm
evidência de Encerrado com diferença de timestamp e 16 código 5 não têm nome
recuperado nas consultas. Isso não autoriza preenchimento global por código.

## Pipeline ativo

- Cloud Run pipeline-monday, us-central1, comando pipeline-monday, argumentos
  daily,--manifest,/app/pipelines.json. Imagem v6 por digest
  8ef037022627ababefa41268fdbb98f71e8aabb0bc2ed230854ba9074d4d50ee.
- Bucket gglobo-viu-dados-hdg-prd-ppd-pipeline-monday; origem em sla_orcamento,
  controle consolidado em consolidado/diario, arquivo viu2 em
  historico_viu2/viu2_18393336134_20260921.
- Scheduler pipeline-monday-diario ENABLED, 0 6 * * *, America/Sao_Paulo,
  URI aponta pipeline-monday:run. Agenda reativada após conferência da publicação.
- Identidades pipeline-orcamento e scheduler-sla-orcamento ainda utilizadas;
  não excluir contas de serviço por conterem nome antigo.

## Publicações comprovadas

| Tabela | Passagens | Evidência |
|---|---:|---|
| monday_sla_orcamento_viu2 | 14.761 | applied_full_content_verified, migração escopo-sla-v3 |
| monday_sla_orcamento_globocorp | 3.598 | replay n7fxj, bq_publication_confirmed, 2.466 projetos |
| monday_sla_orcamento | 9.648 | execução 9pbqp, publication_verified=true, 2.209 projetos |

Globocorp e consolidada têm corte 2026-09-23T03:00:00Z. Orquestração 9pbqp
terminou success; origem skipped com publicação verificada foi aceita.
Scheduler confirmado por AttemptStarted às 09:00:08Z e AttemptFinished HTTP 200
às 09:00:09Z. Execução pipeline-monday-j5d28 publicou 4.400 passagens/3.014
projetos às 09:07Z, antes do replay v6; orchestration_end success. Esses totais
da manhã foram substituídos pela publicação v6 acima. Validação de negócio/KPI pendente.
monday_log_viu2 continua existente; nenhuma exclusão autorizada/executada aqui.

## Limpeza confirmada

Operador excluiu agenda pipeline-orcamento-diario, job pipeline-orcamento e
bucket gglobo-viu-agenciamento-orcamento-prd após autorização explícita de descarte.
Saída de remoção: 100/100 objetos/versões, bucket 1/1; ausente na listagem final.
Aviso de managed folders sem permissão não impediu remoção do bucket. Soft delete
anterior era sete dias; restauração não foi tentada ou verificada.
Dois jobs/agendas restantes: pipeline-monday e LIA. LIA não modificada.

## Pendências para fechar organização

- Terraform remoto ainda registra recursos: não executar apply/destroy. Configuração
  local inclui contas ativas, permissões, secret e Artifact Registry; não é apenas
  estado do bucket removido. Inventário remoto confirmou referências ao bucket
  excluído e recursos ativos (SAs, IAM, APIs e Artifact Registry); reconciliar
  sem executar destroy/apply legado. Secret local não apareceu nesse inventário remoto.
- Cloud Build usou o bucket _cloudbuild em build SUCCESS em 23/09 às 18:15:49Z.
  Preservar os quatro buckets restantes. Não dar ao runtime acesso ao tfstate.
- Disparo anterior confirmado; observar próxima agenda com v6 e consolidação.
- Decidir retenção de monday_log_viu2 separadamente; não adicionar tabelas técnicas.
- Permissões do runtime: jobUser no projeto, WRITER no dataset; GCS condicionado
  a sla_orcamento, consolidado/diario e fontes fixadas somente leitura.

Nenhuma execução de Terraform ou mudança na LIA faz parte desta entrega.
