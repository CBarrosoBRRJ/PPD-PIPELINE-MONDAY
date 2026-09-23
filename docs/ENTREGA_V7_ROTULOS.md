# V7 rótulos — implantação confirmada pelo operador

Recibo posterior: imagem sha256:881c2f44d802883b2a3dfb5099bf65ce22677babb36fa74316a0e26b19de969a,
migração applied_full_content_verified e execução pipeline-monday-8qbwb com
publication_verified=true. Consolidada 9.648 linhas/2.209 projetos, 32 status
sem classificação. Agenda retomada ENABLED às 06h São Paulo. KPI ainda pendente.
As instruções abaixo são histórico da entrega: não repetir a migração.

## Artefatos

- Código: runtime/pipeline-monday-release-20260923-v7-rotulos.zip
  SHA256 6ce58b1b0450281f59370c51e7637b965cd38325968d3addf7a5edc3c053550b.
- Migração privada: runtime/viu2-rotulos-migracao-20260923-v2.zip
  SHA256 adfa2e2005e5c4dac0d4375b9de5c52e267df429dddb0caf00f1debed01695f3.
- Fonte do coordenador: d0aab3fdb25cb1f3746ee0f1c6db37c419e255034b6ce9786ff3e6d84e78af1e,
  17.486 registros incluindo evidência de exclusão, mesma arquitetura anterior.
  Não é tabela BQ nova nem reinclusão no consumo.
- Tabela histórica: 14.761 registros, artefato SHA256
  0a8016b8dd633fb1e94bc5b7f27c38f3b485174b3f1f76eaa8fa4481c6cf5cea.

Plano remoto anterior: lastModifiedTime 1790178379106, controle consolidado
geração 1790186443122911. São pré-condições históricas, não presumir atuais.
Pré-conferência integral aprovada pelo operador; nada desta migração aplicado.

## Ordem operacional obrigatória

1. Construir imagem v7, executar plan offline e conferir HISTORY_SHA embutido;
   publicar no Artifact Registry e registrar digest. Não trocar job diário ainda.
2. Transferir ZIP de migração e conferir checksum. Executar migrate_labels.py plan.
3. Pausar somente pipeline-monday-diario; confirmar ausência de execuções ativas.
4. Configurar pipeline-monday na nova imagem por digest, comando pipeline-monday,
   argumentos plan,--manifest,/app/pipelines.json (impede execução diária prematura).
5. Garantir objectViewer para a SA runtime somente no novo prefixo de fonte
   historico_viu2/sla_publicado/d0aab3fdb25cb1f3746ee0f1c6db37c419e255034b6ce9786ff3e6d84e78af1e/.
   Preservar demais bindings; nunca conceder acesso ao Terraform ou à LIA.
6. Executar migrate_labels.py apply com expected-modified, expected-generation
   recém-conferidos e expected-image igual ao digest da imagem v7. Script verifica
   pacote, base BQ, agenda, modo plan, execuções; preserva histórico completo de
   escopo na fonte, carrega tabela histórica atomicamente e confere conteúdo.
7. Troca apenas identity.history_sha do controle via if-generation-match;
   active continua descrevendo publicação consolidada anterior até reconstrução.
   Falha no CAS: manter agenda pausada, não apagar controle/travas nem forçar troca.
8. Restaurar daily no job v7, executar manualmente e exigir publicação consolidada
   verificada e sucesso da orquestração. Só então retomar agenda e registrar recibos.

Não executar migração via ZIP antigo de escopo. Não reativar v6 após trocar a
identidade: a divergência é bloqueada de propósito. Em resultado incerto, repetir
a mesma migração após inspeção; job ID determinístico reconcilia carga já concluída.
Se o controle já estiver na identidade nova, a retomada não o sobrescreve.
Não há transação única entre BQ/GCS/Cloud Run; agenda pausada e modo plan delimitam
a janela operacional. Não permitir outro operador escrevendo durante a migração.

Precondições GCS: https://docs.cloud.google.com/storage/docs/request-preconditions

## Limites da entrega

Não aprova KPI nem continuidade entre contas. 32 status continuam não classificados
na candidata consolidada. Regras e testes locais atualizados; GitHub sem push e
GCP agora v7 conforme recibo acima. Release-manifest.json registra hashes dos 74
arquivos de código; revisar commit/segredos antes de finalizar sincronização Git.
