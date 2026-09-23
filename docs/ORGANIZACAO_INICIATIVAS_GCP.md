# Um projeto GCP da área, múltiplas iniciativas

Projeto corporativo existente: `gglobo-viu-dados-hdg-prd`. Abriga iniciativas
independentes; não pertence exclusivamente a Pipeline Monday. Não renomear ou
alterar políticas globais desse projeto para atender uma iniciativa.

## Padrão recomendado

| Recurso | Pipeline Monday | LIA / demais iniciativas |
|---|---|---|
| Código | Repositório PPD-PIPELINE-MONDAY | Repositórios próprios |
| GCS | Bucket dedicado já existente `gglobo-viu-dados-hdg-prd-ppd-pipeline-monday` | Buckets próprios conforme necessidade; inventariar antes de propor mudanças |
| Processamento | Coordenador pipeline-monday e produtos em subpastas | Jobs/serviços independentes |
| Agenda | Agenda específica do Pipeline Monday | Agendas próprias, intocadas nesta entrega |
| Identidade | Service accounts próprias com privilégio mínimo | Identidades próprias |
| BigQuery | Tabelas monday_*; dataset atual viu_agenciamento preservado | Datasets por domínio/iniciativa quando apropriado; nenhuma migração implícita |
| Segredos | Segredos da iniciativa com acesso explícito | Sem reutilização automática entre iniciativas |
| Operação | Métricas, alertas e rótulos próprios | Responsáveis/alertas próprios |

Um bucket por iniciativa é um bom ponto de partida, não uma regra de que toda
iniciativa precisa de exatamente um bucket. Criar buckets adicionais quando
região, retenção, sensibilidade ou controle de acesso diferirem. Pastas/prefixos
organizam arquivos, mas não são por si só uma barreira de segurança.

## Permissões e dados compartilhados

Usar IAM no bucket com acesso uniforme e restrições ao recurso específico,
conforme política corporativa. Identidades de execução e de agendamento não devem
receber papéis amplos de administração do projeto por conveniência.
Permissões herdadas do projeto/organização continuam efetivas: nomes distintos
não garantem isolamento de acesso. Mudanças corporativas exigem governança própria.

BigQuery armazena as tabelas gerenciadas; elas não ficam dentro do bucket. O bucket
guarda evidências, arquivos, checkpoints e backups. Para compartilhar dados com LIA
ou ML no futuro, conceder leitura explícita de tabelas/views homologadas, não acesso
de escrita ao bucket/checkpoint da outra iniciativa. Compartilhamento depende de
necessidade/autorização, não apenas de ambos estarem no mesmo projeto GCP.

Para novos datasets, preferir separação por domínio/iniciativa e público consumidor.
Nesta entrega, manter `viu_agenciamento` e seus contratos; não mover tabelas ou
revogar permissões existentes sem inventário de dependências e migração aprovada.

Rotular recursos onde suportado com initiative, environment, product e owner,
usando valores não pessoais aprovados. Medir custo/consumo por iniciativa, mas
orçamento/quotas regionais e de projeto podem continuar compartilhados. Separação
de buckets não elimina disputa por quotas, acesso herdado ou efeitos de políticas globais.

## Estado e escopo

LIA está fora do escopo de mudanças. Não foi verificado se já possui bucket
dedicado e não foi criado/migrado qualquer recurso seu. Esta é uma recomendação
de organização, não uma declaração de que o isolamento IAM já foi auditado.
O bucket dedicado do Pipeline Monday já guarda o resgate; o estado corrente ainda
precisa ser migrado do bucket antigo. O coordenador está em implementação local,
não substitui ainda o job remoto. ML futuro é iniciativa separada, sem configuração agora.

## Possível reorganização da LIA

O usuário levantou a possibilidade de mudar o nome do bucket da LIA, condicionada
a não interromper sua operação. Nenhuma alteração está em execução: o bucket e suas
dependências ainda não foram inventariados. Nome de bucket não é editável; exige
novo bucket, cópia verificada, tratamento das escritas durante a cópia, ajuste dos
consumidores/produtores, notificações, permissões e teste de retorno ao anterior.
Não prometer migração sem interrupção sem comprovar suporte a essa estratégia.
Primeiro concluir Pipeline Monday; avaliar a LIA separadamente com inventário
somente leitura e plano específico. Não excluir seu bucket ou mover arquivos in-place.
Referência: https://docs.cloud.google.com/storage/docs/buckets

Referências:
- https://docs.cloud.google.com/storage/docs/uniform-bucket-level-access
- https://docs.cloud.google.com/bigquery/docs/control-access-to-resources-iam
- https://docs.cloud.google.com/run/docs/securing/service-identity
