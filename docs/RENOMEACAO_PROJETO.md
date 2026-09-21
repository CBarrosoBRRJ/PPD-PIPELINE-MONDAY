# PIPELINE-MONDAY — transição do nome do projeto

Decisão de 21/09/2026: o projeto e repositório passam a se chamar `PIPELINE-MONDAY`. `sla_orcamento` é o primeiro produto de dados, com seu contrato vigente preservado. A publicação de outras tabelas ainda depende de especificação e implementação conforme [continuidade](CONTINUAR_NO_VSCODE.md).

## Cópias locais e Cloud Shell

Na pasta do clone existente, atualize o remoto:

```bash
git remote set-url origin https://github.com/CBarrosoBRRJ/PIPELINE-MONDAY.git
git fetch origin
git status -sb
```

O nome da pasta de um clone é independente do nome do repositório. Cópias já abertas podem manter a pasta anterior; os comandos `cd PIPELINE-MONDAY` nos guias correspondem a clones novos. Para renomear uma pasta existente, feche processos que a utilizem, renomeie-a para `PIPELINE-MONDAY` no diretório pai e reabra o projeto pelo novo caminho. Confira atalhos e ambientes virtuais com caminhos absolutos antes de utilizá-los.

O GitHub mantém redirecionamentos do endereço antigo. Não recrie outro repositório com o nome antigo, pois isso remove o redirecionamento. O histórico, branches e identidade numérica do repositório são preservados.

## Integração GitHub/GCP

`infra/main.tf` usa `CBarrosoBRRJ/PIPELINE-MONDAY` como valor padrão de `github_repository`. O provider Workload Identity Federation também verifica esse nome em `assertion.repository`, além dos IDs numéricos e da branch `main`.

Antes de usar o deploy via GitHub Actions, o operador deve conferir o provider real e eventuais variáveis privadas que sobrescrevam `github_repository`. Se o provider já existir com o nome antigo, atualizar somente essa condição para o novo nome, preservando IDs, restrição de branch e demais condições. A alteração do arquivo Terraform não atualiza o provider implantado.

Há provisionamento manual e estado parcial documentados. Reconciliar os recursos/estado e revisar um plano antes de aplicar Terraform; não executar `apply` ou `destroy` apenas para sincronizar o nome. Se a federação ainda não existir, usar o novo nome ao configurá-la. Validar a autenticação antes do próximo deploy manual do workflow.

A renomeação não exige reinicializar a base, executar coleta nem republicar a imagem. O Job e Scheduler existentes continuam vinculados aos recursos GCP já configurados. As outras cópias, incluindo Cloud Shell, precisam atualizar seu remoto separadamente.

## Identificadores preservados

- Pacote/distribuição do produto: `sls_orcamento_ppd` / `sls-orcamento-ppd`; CLI `sla-pipeline`.
- Destino: `gglobo-viu-dados-hdg-prd.viu_agenciamento.sla_orcamento`.
- Job, imagem, Scheduler, service accounts, bucket/prefixos e backend Terraform existentes.
- IDs Monday, namespaces de UUID/SK, identidade do pipeline, checkpoint, Bronze e contratos.

Esses identificadores pertencem ao produto de orçamento. Uma futura reorganização do pacote deverá tratar compatibilidade explicitamente. Origem, grão, tipos, chaves, nulabilidade, regras de cálculo, consumidores e comportamento em falha do produto não mudam nesta renomeação.
