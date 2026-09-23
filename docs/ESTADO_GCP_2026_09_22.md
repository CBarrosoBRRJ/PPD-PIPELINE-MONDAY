# Evidências fornecidas pelo operador em 22/09/2026

Atualização do registro de 21/09; não implica acesso GCP pelo agente local.

- Estado operacional copiado ao bucket `gglobo-viu-dados-hdg-prd-ppd-pipeline-monday`,
  prefixo `sla_orcamento`: 52 objetos, 148,1 MiB, comparação por checksum sem diferenças.
- Job antigo teve GCS_BUCKET atualizado. Recover krdnx e validate-gold qjfbk concluídos.
- Execução `pipeline-orcamento-nq75h` publicou 4.237 linhas e terminou success em
  22/09 16:08:59 UTC; nova publicação pelo bucket novo comprovada.
- Coordenador `pipeline-monday` criado com 2 CPU/8 GiB/3600s/maxRetries=0,
  imagem por digest `sha256:a33f6bfb51c1f4b0157fd64d9b5384fa7631e013f9673dbcd0bea8dbf9c979f8`.
- Configuração do job antigo copiada por lista permitida, referência Monday secret
  versão 1 preservada (sem valores de token). Execução 4j2k4 retornou skipped por
  daily_already_claimed; não houve publicação comprovada por esse coordenador ainda.
- Argumentos padrão agora daily,--manifest,/app/pipelines.json. Agenda
  pipeline-monday-diario ENABLED às 06h America/Sao_Paulo; antiga PAUSED.
  LIA mantém sua agenda ENABLED a cada três minutos e o mesmo destino; isolamento
  completo de permissões/dependências ainda não auditado.
- Log viu2 copiado para monday_log_viu2: 133.611 linhas, conteúdo/repetições iguais,
  schema igual, sem expiração e nenhuma view dependente retornada no dataset.
  Operador excluiu log_monday_viu2 e confirmou listagem sem o nome antigo.
- Permanecem sla_orcamento e backup_sla_orcamento_pre_migracao_20260921.
- Controle consultado: format=1, location=US, timezone=America/Sao_Paulo,
  pipeline=sls_orcamento_pdd:18429499488:status_19, table termina em sla_orcamento,
  pending ausente e gold_hash presente. Preservar identificador interno pdd para
  compatibilidade: não é erro a corrigir por busca/substituição.

Preparação local: rename-sla-plan/apply introduzidos no pacote v3-validado;
178 testes passaram, 3 ignorados. Nenhuma migração de identidade aplicada no GCP.
Histórico SLA viu2, correspondência de projetos e consolidado continuam pendentes.

## Atualização posterior: migração aplicada pelo operador

Esta seção substitui o estado de preparação acima, mantendo a cronologia.

- Imagem v3 implantada por digest `sha256:390baea45dff65b0b1d72593b24ebe8766a28c6b53965af96776c7a0e2e5e7bc`.
- Cópia sem sobrescrita para `monday_sla_orcamento_globocorp` concluída.
- Plano `pipeline-monday-vb2zs` e aplicação `pipeline-monday-qbv6h` concluídos;
  recibo informa `applied: true`. Identidade do controle migrada para o novo destino,
  com backup em `sla_orcamento/backups/rename_destination_b1b8504b9140463499ed54a2ff9c3450/control.json`.
- BQ_TABLE do coordenador atualizado; `validate-gold` na execução
  `pipeline-monday-6nctr` terminou com sucesso. Não equivale a uma nova coleta.
- Operador restaurou comando `pipeline-monday`, argumentos `daily,--manifest,/app/pipelines.json`
  e retomou `pipeline-monday-diario`. Publicação diária pelo coordenador ainda requer recibo.
- Não executar o job antigo: seu destino não acompanha a identidade atual do controle.

## Complemento local do resgate

- Revisão direcionada da API: 449 eventos, nenhum ID novo nem payload alterado frente
  ao arquivo original. Não inserir esses eventos novamente no BigQuery.
- Pacote `runtime/archives/viu2-complemento-20260922-v1-gcp.zip`: 32.679 bytes,
  15 arquivos do complemento e relatório comparativo. Hashes do manifesto local
  conferidos e integridade ZIP testada.
- SHA256: `167c4b7dfe1a1fe6b2116bd51369f9da6ba1352a45f87cfb7d7d39ba3d8ecc63`.
- Envio deste complemento ao GCP ainda pendente; não confundir com o resgate original
  já verificado no GCP. Lacunas de lotes continuam documentadas; SLA histórico e
  consolidação não estão liberados para KPIs.

### Complemento confirmado no GCP pelo operador

O operador enviou o ZIP com `gcloud storage cp --no-clobber` e leu o objeto
novamente com `gcloud storage cat | sha256sum`, com pipefail habilitado.
Destino: `gs://gglobo-viu-dados-hdg-prd-ppd-pipeline-monday/historico_viu2/complementos/viu2-complemento-20260922-v1-gcp.zip`.
SHA256 remoto igual ao local: `167c4b7dfe1a1fe6b2116bd51369f9da6ba1352a45f87cfb7d7d39ba3d8ecc63`.
Isso encerra a pendência de envio acima, sem inserir eventos duplicados no BigQuery.
Não comprova completude vitalícia da origem, imutabilidade por retenção bloqueada,
publicação do SLA histórico ou execução diária do coordenador.

## Preparação local posterior — contrato de revisão

Implementado contrato separado sla-viu2-review-v1, sem modificar contrato corrente,
imagem implantada, escritor, agenda ou GCP. Exportadas 17.486 linhas privadas,
relidas e validadas; manifesto publication_allowed=false e kpi_approved_rows=0.
Local: runtime/validation/viu2_review_export_20260922_v1. SHA256 do gzip:
e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532.
Suite completa: 215 passed, 3 skipped; Ruff histórico passou.
Contrato/documentação gerados por generate_review_contract_docs.py.
Pendências externas e plano de limpeza sem exclusões: docs/FECHAMENTO_ENTREGA_MONDAY.md.
Dados disponíveis preservados não equivalem a SLA histórico/consolidado homologados.

## Seleção local de identidade — após diagnóstico de Encerrado

Mapa privado gerado e relido: 4.294 pares selecionados pela regra aceita pelo
usuário, 74 itens viu2 do contexto excluídos da ligação, sem exclusão de raw.
Arquivo `runtime/validation/selected_identity_20260922_v1/selected_identity.json.gz`.
SHA256: `486845629229aaa881c38ab87d58cec49811f539642d413d9aa29f07569399eb`.
O arquivo não está no GCP ainda. Nenhuma tabela, agenda, job, bucket ou IAM foi
alterado nesta etapa. Identidade selecionada não aprova tempos na fronteira.

Captura local somente leitura do globocorp: 1.986 eventos disponíveis da coluna
status_19, com manifesto e checksums em
`runtime/archives/globocorp_status_validation_20260922_v1`.
Diagnóstico por projeto em `runtime/validation/closed_trajectory_both_20260922_v1.json`:
3.109 encerrados no contexto; 3.059 classificados, 47 sem ligação selecionada e
3 sem transições recuperadas. Um classificado tem apenas Encerrado. Estados
anteriores explícitos são considerados sem inventar início/duração.

## Recibo da carga histórica com nome final

Operador executou o pacote viu2-sla-bq-20260922-v1.zip após SHA256 OK.
Recibo: historical_loaded_schema_and_count_verified; tabela
gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento_viu2;
17.486 linhas; job historical_sla_viu2_v1_e3cb6b12674bed2591df6ea9;
expiration_time=null; kpi_approved=false.
SHA256 do artefato fonte:
e3cb6b12674bed2591df6ea9f14a0591619f817d332b495251dcfd901b7e2532.
Captura do explorador também mostra o nome novo. A confirmação cobre schema e
quantidade, não reconciliação integral de todas as células remotas nem homologação
de negócio. Preservados os nomes legados/backup; sem alteração LIA ou agenda.

## Consolidado preparado localmente, ainda não publicado

Export globocorp fornecido pelo operador e conferido localmente: 4.237 linhas,
SHA256 3f3d07cef374f11b3b6811364e62099ca81c4a517026dbdefbc7798f29ec83e7.
Versão candidata final desta etapa: consolidated_20260922_v3; contrato separado
sla-consolidado-evidencias-v2. 11.252 passagens de 2.640 projetos, sendo 10.977
linhas viu2 e 275 globocorp. 2.645 referências globocorp sem entrada comprovada
ficam fora; preservadas na origem. Cinco pares presentes na Gold não tinham
passagem datada nas fontes selecionadas. Os 1.649 pares sem item na Gold atual
não são reinseridos automaticamente, e sua ausência não tem causa presumida.

Terminais encerram SLA na entrada: Encerrado e os dois Declinados. Há 2.340
passagens terminais, 1.314 ciclos locais com Entrada e continuidade comprovadas,
64 reaberturas locais comprovadas. Esses números NÃO são contagem de projetos
homologados nem comprovam continuidade na migração. Sem total entre contas.
Negócio Fechado continua como expansão futura configurável.

Pacote de primeira carga usa WRITE_EMPTY, nome monday_sla_orcamento, verificação
dos timestamps de modificação das fontes, checksums GCS, schema e releitura
integral do destino. Não instala atualização diária nem modifica as origens.
Integração no coordenador, homologação e limpeza GCP continuam pendentes.

## Recibo posterior: consolidado publicado e integralmente conferido

O operador confirmou conteudo_integral_conferido para monday_sla_orcamento:
11.252 linhas e 2.640 projetos. Conferência independente verificou schema,
contagem, fingerprint integral e lastModifiedTime estável durante a leitura.
Consulta: bqjob_r7eaa77e829d69900_000001a0cc007f4f_1.
Isso supera a pendência de publicação acima, mas não aprova KPIs e não instala
atualização diária. A falha anterior de --account no bq ocorreu na conferência
pós-carga; não exige recarregar a tabela já conferida.

Decisão posterior: retirar do BQ sla_orcamento e
backup_sla_orcamento_pre_migracao_20260921, após arquivamento verificado no GCS
e análise de dependências. Não criar outro dataset de backups. Nenhuma dessas
duas exclusões foi executada ou confirmada nesta etapa. Recursos LIA intocados.

## Recibo posterior de limpeza do BigQuery

Operador confirmou ausência de consumidores e excluiu explicitamente
backup_sla_orcamento_pre_migracao_20260921 e sla_orcamento. Listagem e captura
mostram apenas as quatro tabelas monday_*. Arquivos Avro/metadados permanecem em
recuperacao/bq_legados/20260923T021051Z-monday-legados-P5Fb0t no bucket dedicado.
Contagens 4.105/4.237 conferidas; comparação JSON bruta divergiu por representações
Avro (TIMESTAMP lido INT64, DATETIME STRING nos campos examinados). Não declarar
restauração integral verificada. Não excluídos jobs/buckets nesta etapa.

Implementação diária local posterior: docs/ATUALIZACAO_DIARIA_CONSOLIDADO.md.
Imagem e agendamento remoto ainda não incorporam essa alteração até novo recibo.
