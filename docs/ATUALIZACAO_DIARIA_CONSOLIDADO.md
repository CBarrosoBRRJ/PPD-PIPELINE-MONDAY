# Atualização diária da consolidação — implementação local

Não implica imagem implantada nem execução GCP comprovada.

Atualização v5: escopo-sla-v3 e pastas por tabela implementados. A evidência v4
ao fim deste documento é histórica, anterior aos filtros. Seguir
[entrega v5](ENTREGA_V5_ESCOPO.md) antes de implantar. VIU2_ARCHIVE_PREFIX deve
identificar o resgate com board.json.gz e context/context_manifest.json cujos
checksums estão fixados no código. Não adivinhar esse prefixo nem mudar BQ_TABLE.
O SLA histórico já publicado precisa de atualização única controlada; a rotina
diária não escreve essa tabela e não resolve essa migração automaticamente.

## Contrato operacional

Fonte corrente: monday_sla_orcamento_globocorp, tabela real conferida com o
checkpoint existente, sob a mesma trava do escritor. Corte deve ser exatamente
o fechamento D+1 em America/Sao_Paulo da execução solicitada.
Fonte congelada: artefato histórico viu2 publicado, fixado por SHA256.
Mapa: 4.294 pares da política selecionada pelo usuário, fixado por SHA256.
Sem nova extração viu2 e sem revisão automática de correspondências por nome.
Novos itens sem correspondência continuam fora da consolidação, presentes na
origem: avaliar produto/contrato para projetos exclusivamente globocorp depois.

Destino único: viu_agenciamento.monday_sla_orcamento. Grão, campos, nulos,
chaves e restrições permanecem os do contrato sla-consolidado-evidencias-v2.
Não aprova negócio/KPI/ML nem continuidade entre contas. Não altera terminais.

O manifesto roda sla_orcamento antes de monday_sla_orcamento. Um skipped da
origem só libera o dependente após nova verificação de publicação e fechamento;
uma reserva diária por si só não é evidência. O consolidado também verifica
fonte, corte e etag por conta própria. As duas verificações são intencionais.

`globocorp-runtime` é seletor explícito da configuração de origem herdada do
ambiente do job (load_settings('.env')), não nome de arquivo secreto. O adaptador
fixa outro destino e outro prefixo; NÃO mudar BQ_TABLE nem GCS_PREFIX do job.
O contrato de execução permanece um único board globocorp configurado.

## Publicação e falhas

Travas: primeiro sla_orcamento/writer.lock, depois consolidado/diario/writer.lock,
no bucket dedicado ppd-pipeline-monday. Nunca expiram automaticamente.
Controle separado consolidado/diario/control.json identifica destino/contrato/mapa.
Na primeira execução, só adota a tabela existente se o conteúdo integral corresponder
ao pacote inicial conferido pelo operador. Não aceita tabela vazia ou divergente.

Artefato NDJSON e relatório de exclusões privados em gerações GCS; journal grava
job ID antes da submissão. WRITE_TRUNCATE é atômico, CREATE_NEVER impede recriar
um destino excluído acidentalmente. Falha terminal conserva conteúdo anterior;
resultado incerto preserva pending e impede outra carga até resolver o mesmo job.
Confere schema, conteúdo integral e estabilidade de etag antes de promover active.
Conteúdo repetido é verificado e reutilizado, sem outro load. Corte regressivo
ou lote vazio bloqueia. Nenhuma tabela de staging/backup é criada no BigQuery.

Esses artefatos são estado operacional de recuperação, não backups de implantação
descartáveis. Não apagar control, pending, locks ou gerações referenciadas para
reduzir a lista de objetos. Não há coleta automática de lixo nesta versão.

## Implantação controlada

1. Gerar release novo por allowlist; plano offline deve mostrar dois produtos.
2. Pausar apenas pipeline-monday-diario e confirmar ausência de execuções ativas.
3. Guardar digest/configuração atual para rollback. Implantar novo digest no mesmo
   job, preservando service account, secrets, recursos, BQ_TABLE e prefixo da origem.
4. Executar daily e exigir consolidated_publication_confirmed com
   publication_verified=true e corte esperado, mais orchestration_end success.
5. Conferir BQ/control e retomar agenda; observar disparo automático às 06h.
6. Só então encerrar recursos antigos; nunca executar pipeline-orcamento legado.

Rollback do executor só com escritores parados e pending resolvido. Imagem v3
atualiza apenas globocorp: rollback não é continuidade da atualização consolidada.
Imagem fixa artefatos iniciais por hash; alteração deles exige migração explícita.
Memória 8 GiB não é garantia: medir pico/duração ao executar os dois produtos.

Recuperação sem nova extração é suportada pelo módulo worker_consolidated com
--recover-only, --env-file globocorp-runtime, --scheduled-for com fuso e --result
em caminho temporário novo. Verifica e resolve pending, sem avançar novo corte.
Morte abrupta exige primeiro confirmar término/cancelamento da execução Cloud Run,
inspecionar lock do prefixo correto e liberar apenas sua geração exata. Nunca
usar unlock do produto globocorp para remover a trava da consolidação.

## Pendências separadas

Reorganização completa das pastas por tabela, limpeza de recursos legados,
alertas, IAM e homologação de negócio não são efeitos da implantação deste pacote.
LIA, Cloud Build, estado Terraform e buckets compartilhados permanecem intocados.

## Evidências locais do candidato v4

- Suite completa: 267 passed, 3 skipped; Ruff orquestracao passou.
- Reexecução local das fontes conferidas: 11.252 linhas / 2.640 projetos,
  fingerprint e751c89fdc962b5cec322d14c6dca2f1c9bfcede21a22a1bf87ce69a16ccf543,
  idêntico à primeira carga consolidada.
- Testes incluem adoção inicial divergente, edição externa, lote vazio, corte
  antigo, carga recusada, timeout, submissão sem confirmação, job incompatível,
  artefato corrompido e repetição sem novo load.
- Release: runtime/pipeline-monday-release-20260923-v4-diario.zip, 65 arquivos
  de código/metadados; SHA256
  83949392a97eec690d605da6e09ae64c90420c7506988a959d06b7b84d692221.
- Não executado build Docker nem implantação/publicação deste candidato no GCP.
  Próxima ação externa: upload do ZIP pelo operador para Cloud Shell.
