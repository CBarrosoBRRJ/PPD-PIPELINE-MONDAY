# Padronização aprovada — origem, tema e ambiente

Solicitação e aprovação do usuário em 21/09/2026. Convenção: `<origem>_<tema>[_<ambiente>]`,
minúsculas, snake_case, sem acentos. Origem identifica o sistema (monday), não o
projeto GCP. Ambiente só é usado em produtos específicos de uma conta; o produto
unificado não recebe esse sufixo. Preferir `globocorp`, nome da origem, a `globo`.

| Nome anterior/planejado | Nome proposto | Papel |
|---|---|---|
| log_monday_viu2 | monday_log_viu2 | Eventos resgatados, congelados |
| sla_orcamento_viu2 | monday_sla_orcamento_viu2 | SLA histórico congelado após validação |
| sla_orcamento_globocorp | monday_sla_orcamento_globocorp | SLA específico da origem nova, diário |
| sla_orcamento (unificada planejada) | monday_sla_orcamento | Trajetória integrada e referência para KPIs |

A tabela `sla_orcamento` existente ainda é a versão anterior, não a unificada.
Esta proposta não altera tabelas GCP, escritores, prefixos ou chaves automaticamente.
Não renomear IDs/SKs ou checkpoints por uma decisão de apresentação dos produtos.

## Troca controlada

## Nível compartilhado e produtos

Diretriz confirmada pelo usuário: recursos de nível geral não recebem `orcamento`.

| Escopo | Padrão/nome | Estado |
|---|---|---|
| Projeto de código | PPD-PIPELINE-MONDAY | Nome do repositório |
| Família da plataforma | pipeline-monday | Convenção geral |
| Bucket dedicado | gglobo-viu-dados-hdg-prd-ppd-pipeline-monday | Resgate, complemento e estado corrente preservados; bucket antigo retido para recuperação |
| Coordenação geral | pipeline-monday / pipeline-monday-diario | Coordenador implantado com um produto; agenda habilitada, primeira publicação diária ainda por comprovar |
| Execução de produto | Adaptador sla_orcamento no coordenador | Não criar job adicional concorrente; pipeline-orcamento antigo não deve ser executado |
| Tabela de consumo | monday_sla_orcamento | Produto orçamento, não nome da plataforma |

Coordenação geral deve disparar produtos respeitando suas dependências e registrar
resultados separados. Não basta renomear o job atual para torná-lo multiproduto:
o manifesto implantado ainda contém exclusivamente SLA orçamento. Não criar agenda geral
concorrente com agendas específicas para o mesmo escritor. Falha de um produto
deve bloquear seus dependentes, sem apresentar dados antigos como atualização nova.

Pastas por produto continuam `tabelas/<produto>/`; regras, contratos, prefixos de
estado e locks específicos não serão movidos para uma camada master genérica.
Infra/documentação compartilhadas ficam na raiz. Uma futura biblioteca comum
não deve incorporar dependências de negócio exclusivas do orçamento.
Não renomear o projeto GCP corporativo compartilhado, o dataset existente,
identidades ou recursos da LIA para adequá-los ao nome deste repositório.

## Procedimento de troca

Convenção confirmada; atualizar contratos/documentação, escritores,
consumidores e pastas de produto de modo consistente. Manter backup recuperável,
resolver pending/lock e validar novas cargas antes da troca dos consumidores.
Não criar uma segunda cópia do log como se fosse nova evidência de extração.
Reconciliar quantidade, schema e conteúdo antes de retirar o nome antigo.
Conferir views, relatórios e consultas dependentes antes de excluir tabela legada.
O estado não migra apenas com BQ_TABLE: a identidade e referências GCS precisam
ser reconciliadas. A agenda deve ser retomada somente após validar o escritor certo.

Escopo: somente os produtos Monday/orçamento autorizados. Nenhuma padronização
global do dataset/projeto, nenhuma alteração da LIA ou de recursos de terceiros.
