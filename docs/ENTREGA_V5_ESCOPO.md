# Entrega v5 — código local, implantação pendente

## Pacote

runtime/pipeline-monday-release-20260923-v5-escopo.zip, 74 arquivos de código e
metadados, mais inventário de hashes; sem .env, dados, tokens ou estado.
SHA256: 30c382b9019e67a986e6f2a4944d7bc25555d06d4b4cb48b913518dedef28166.
Não sobrescreve v4. Não é autorização para implantar antes do preflight abaixo.

## Evidência local

- Suite: 325 passed, 3 skipped. Ruff passou.
- Docker build concluído com pip check; teste offline sem rede planejou os dois
  produtos na ordem correta. Usuário não root (UID 10001), imports do worker e
  contexto histórico funcionando; política escopo-sla-v3 confirmada na imagem.
- Imagem local pipeline-monday:20260923-v5-escopo. Não enviada ao registry GCP.

Replay com cadastro viu2 validado pelos mesmos hashes usados pelo worker:
9.638 passagens / 2.209 projetos consolidados. Conteúdo dos projetos mantidos
idêntico à primeira publicação: fingerprint
de58d2319918647f4a236455dc9445055c057e2e8e58582ccf8469c4f88411a1.
Filtrar não reescreve datas, IDs, valores ou durações dos projetos retidos.
Histórico após recorte: 14.761 passagens. Não são contagens verificadas no GCP.

## Bloqueio externo identificado

Consulta local ao job retornou PERMISSION_DENIED (run.jobs.get). Consulta ao
bucket retornou 403 e identidade efetiva inconsistente com a conta selecionada.
Nenhuma credencial, política IAM, agenda ou recurso remoto foi alterado.
Usar sessão Cloud Shell do operador; não pedir token em chat e não conceder
papéis amplos para contornar esse erro.

## Ordem restante

1. Ler configuração atual do job, agendas, execuções e prefixo do arquivo viu2;
   confirmar acesso aos objetos fixados e estado sem pendências.
2. Preparar atualização única do histórico: comparar conteúdo remoto com a fonte
   original fixada; aplicar recorte, conferir schema/conteúdo integral e não
   recriar tabela nem criar backup/staging BQ. O publicador de primeira carga
   WRITE_EMPTY não serve para essa atualização. Implementação posterior disponível
   no pacote de migração abaixo; execução remota ainda pendente.
3. Com agenda do pipeline pausada e nenhum escritor ativo, implantar imagem por
   digest preservando identidade, env, secrets, recursos e prefixos existentes.
4. Publicar origem globocorp com regras novas e depois consolidação; se daily
   estiver reservado, não apagar a reserva nem repetir unlock às cegas. Validar
   possibilidade de replay/reprocessamento pelo contrato do executor.
5. Exigir verificação integral, corte esperado e recibos de publicação. Retomar
   agenda somente após isso; observar execução automática às 06h Brasília.
6. Inventariar dependências de recursos legados antes de excluir. LIA, recursos
   compartilhados, estados e buckets não foram autorizados para remoção indiscriminada.

Não declarar que todas as tabelas estão filtradas ou atualizando enquanto essas
etapas estiverem pendentes. Homologação de KPI é separada da implantação técnica.

## Migração histórica separada preparada

Arquivo: runtime/viu2-sla-escopo-20260923-v1.zip.
SHA256: 80478f99b83f9a0c42bfbf9410beaed016b7fd7f6dcbc450cf7984335e39334f.
Inclui original tratado para comparação local, subconjunto tratado, schema,
manifesto e script. Não contém tokens ou raw Monday. Não envia o original ao GCS.
Somente `python3 migrate_scope.py plan` está liberado para o próximo passo:
confere identidade corporativa, localização, schema, ausência de expiração e
conteúdo integral estável contra a primeira carga. Imprime expected_modified.

`apply --expected-modified VALOR` exige as duas agendas do pipeline pausadas,
nenhuma execução em aberto, conteúdo antigo integralmente conferido, revisão do
plano e a mesma versão remota. Escreve somente artefato tratado no prefixo
historico_viu2/sla_publicado/hash; carrega a tabela existente com CREATE_NEVER,
WRITE_TRUNCATE e job ID determinístico. Não cria tabelas auxiliares.
Escritores externos não cooperativos continuam proibidos durante a manutenção:
o BigQuery load não oferece CAS pela etag da tabela. Verificações antes/depois
detectam alterações, mas não substituem exclusividade de escrita.

Repetição com destino já igual apenas verifica. Job existente é reconciliado;
timeout não autoriza trocar ID, remover estado ou executar carga manual.
Falha bloqueia conclusão. Confirmação final exige schema, contagem e fingerprint.
Esse pacote não altera imagem, agenda, consolidada, globocorp ou LIA.

Recibos do operador: imagem v5 enviada ao registry com digest
348c5105c1983744f4053aeab8649887f1b29518ef262b33c595b033eae4c95b;
job ainda v3; agenda monday habilitada e antiga pausada. Prefixo viu2 confirmado
historico_viu2/viu2_18393336134_20260921, hashes de board/context iguais aos locais.
