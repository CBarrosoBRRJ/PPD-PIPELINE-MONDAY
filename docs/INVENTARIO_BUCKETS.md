# Inventário de buckets — evidências e decisão de organização

**Atualização confirmada em 23/09:** bucket legado gglobo-viu-agenciamento-orcamento-prd
excluído pelo operador, inclusive objetos/versões listados. Pipeline ativo usa o
bucket ppd-pipeline-monday e publicou com sucesso. LIA preservada. Cloud Build e
Terraform ainda não liberados para exclusão. Ver [recibo atual](ESTADO_GCP_2026_09_23.md).
O restante deste documento registra o levantamento histórico de 21/09, não ações
a repetir nem comandos autorizados para a configuração atual.

Base: captura do Console enviada pelo usuário e referências locais em 21/09/2026.
Não é auditoria completa de IAM, objetos ou consumidores remotos. Nenhum bucket
foi excluído, migrado ou renomeado por este inventário.

| Bucket | Papel observado/provável | Decisão segura |
|---|---|---|
| gglobo-viu-agenciamento-orcamento-prd | Estado atual confirmado do Job pipeline-orcamento; prefixo sla_orcamento | Legado candidato a retirada somente após migração validada de objetos/estado, IAM, job e consumidores |
| gglobo-viu-dados-hdg-prd-ppd-pipeline-monday | Bucket dedicado; contém o resgate viu2 publicado | Manter como destino da iniciativa Pipeline Monday |
| gglobo-viu-lia-dados-prd | Nome indica dados da LIA; dependências não inventariadas | Preservar; não há justificativa de renomeação puramente estética |
| gglobo-viu-dados-hdg-prd_cloudbuild | Nome padrão para arquivos de origem enviados ao Cloud Build; builds específicos ainda não auditados | Técnico; pode atender várias iniciativas. Não confundir com bucket de tabelas nem excluir sem verificar builds |
| gglobo-viu-terraform-state-prd | Referenciado nos dois backends Terraform locais | Aposentadoria possível somente após inventariar estado/dependências e preservar recuperação |

## Terraform: configuração não equivale a uso comprovado

### Medição fornecida pelo usuário

- Bucket antigo orçamento: 148,12 MiB.
- Bucket dedicado Pipeline Monday: 30,90 MiB.
- Bucket LIA: 1,66 MiB.
- Cloud Build: 6,01 MiB.
- Terraform: 28,90 KiB; 2 objetos atuais, 29.596 bytes:
  - infra/bootstrap-state/prod/default.tfstate: 4.197 bytes, 16/09/2026 21:09:16 UTC;
  - infra/sla-orcamento/prod/default.tfstate: 25.399 bytes, 16/09/2026 21:30:57 UTC.

Os estados existem, mas seu conteúdo e consumidores não foram auditados. Não
apagar nem expor tfstate no chat. Não copiá-lo para prefixo acessível à identidade
de execução do pipeline: o arquivo pode conter dados sensíveis de infraestrutura.
As medições não incluem necessariamente versões antigas/soft delete.

Próxima etapa proposta: cópia sem sobrescrita apenas do prefixo sla_orcamento do
bucket antigo para backups/migracao_bucket_20260921/sla_orcamento no bucket dedicado.
Confirmar comparação de conteúdo com rsync --checksums-only --dry-run. Essa cópia
não migra configuração do Job, IAM, gerações antigas ou referências de controle;
não é autorização para excluir o bucket antigo. Agenda continua pausada.

O usuário informa que a operação é feita por código/comandos gcloud/bq, sem usar
Terraform atualmente. Os comandos executados durante a recuperação confirmam esse
fluxo operacional. Contudo, o repositório ainda contém:

- infra/backend.tf, prefixo infra/sla-orcamento/prod;
- infra/bootstrap-state/backend.tf;
- definição e proteções do bucket de estado em infra/bootstrap-state/main.tf;
- CI que executa fmt, init -backend=false e validate.

Essas referências não provam que alguém executa apply atualmente, nem que o bucket
está vazio/inútil. A CI apenas valida configuração e não aplica infraestrutura.
Não executar terraform apply/destroy como parte da limpeza. Antes de remover o
bucket, verificar estados e versões sem expor conteúdo, último uso, dependências
externas e necessidade de guarda para recuperação. Se aposentado, retirar também
as referências e validações Terraform obsoletas de forma coerente, sem destruir
os recursos GCP que eventualmente foram originalmente provisionados por ele.

## Resultado desejado

Dois buckets de dados de iniciativas (LIA e Pipeline Monday), mais buckets técnicos
necessários. Não há requisito de exatamente dois buckets totais. A redução de cinco
para três é apenas uma possibilidade se o legado for migrado e o estado Terraform
for comprovadamente aposentável. Região US do bucket novo e us-central1 do antigo
devem ser consideradas em IAM/localização/transferência e validação BigQuery.

Manter código operacional versionado, escopo explícito e verificações antes/depois.
Não usar scripts de limpeza global do projeto. Volumes medidos por du são inventário,
não prova de inutilidade; versões não correntes e soft delete exigem análise separada.

Referências:
- https://docs.cloud.google.com/build/docs/running-builds/submit-build-via-cli-api
- https://docs.cloud.google.com/sdk/gcloud/reference/storage/du
