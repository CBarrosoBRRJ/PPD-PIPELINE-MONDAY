# infra/ — NÃO aplicar

Este Terraform descreve a infraestrutura **antiga** do pipeline de orçamento e está
fora de sincronia com o GCP real desde a migração de 21–22/09/2026.

Um `terraform apply` hoje faria três coisas erradas:

- recriaria o bucket de estado legado, que já foi excluído;
- trocaria o acesso por prefixo da conta `pipeline-orcamento` por acesso ao bucket inteiro;
- tentaria recriar o segredo `monday-api-token`.

O estado real é administrado pelo operador. Os recibos estão em `docs/ESTADO_GCP_*.md`
e o passo a passo atual em `docs/IMPLANTACAO_V18_1_ESTABILIDADE.md`.

| Pode | Não pode |
| :--- | :--- |
| `terraform fmt -check` e `terraform validate` (o CI roda) | `terraform plan` contra o estado remoto para aplicar |
| Ler para entender o desenho original | `terraform apply` / `destroy` / `import` |

Para voltar a gerenciar por Terraform, é preciso um projeto próprio:

1. importar cada recurso real;
2. rodar um `plan` sem nenhuma mudança;
3. obter aprovação do Caio.

Nunca incluir recursos da LIA nem bindings de projeto inteiro.
