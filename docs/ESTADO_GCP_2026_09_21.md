# Estado observado e isolamento — 21/09/2026

Fonte: saída de comandos somente leitura executados pelo usuário no Cloud Shell
corporativo. Não equivale a reconciliação de conteúdo das tabelas ou a implantação nova.

## Escopo permitido

- Projeto GCP compartilhado: `gglobo-viu-dados-hdg-prd`.
- Job: `pipeline-orcamento`, região `us-central1`.
- Agenda: `pipeline-orcamento-diario`, 06h America/Sao_Paulo, habilitada.
- Identidade do Job: `pipeline-orcamento@gglobo-viu-dados-hdg-prd.iam.gserviceaccount.com`.
- Chamador agendado: `scheduler-sla-orcamento@gglobo-viu-dados-hdg-prd.iam.gserviceaccount.com`.
- Destino atual: `viu_agenciamento.sla_orcamento` (versão anterior, não unificada).
- Bucket atual: `gglobo-viu-agenciamento-orcamento-prd`, prefixo `sla_orcamento`.
- Bucket dedicado de destino: `gglobo-viu-dados-hdg-prd-ppd-pipeline-monday`.
- Histórico já publicado: `viu_agenciamento.log_monday_viu2`.

## Fora do escopo

`lia-leitura-inteligente-scheduler` e todos os recursos associados à LIA são
explicitamente protegidos por determinação do usuário. Não pausar, modificar,
remover, migrar, compartilhar estado nem mudar permissões desses recursos.
Não conceder/revogar permissões amplas no projeto como atalho da migração.
Não remover o bucket antigo inteiro: inventariar e atuar somente nos objetos
autorizados de orçamento, com backup e reconciliação. Não mover estado Terraform.

## Execuções apresentadas

| Execução | Criação UTC | Resultado exibido |
|---|---|---|
| pipeline-orcamento-9d9kp | 21/09 09:00:01 | Falha; 0/1 concluída |
| pipeline-orcamento-mxl5w | 20/09 09:00:01 | Falha; 0/1 concluída |
| pipeline-orcamento-s6dpg | 19/09 09:00:01 | Sucesso; 1/1 concluída |
| pipeline-orcamento-fx9cz | 18/09 13:51:48 | Sucesso; 1/1 concluída |
| pipeline-orcamento-7tbn7 | 18/09 01:38:55 | Sucesso; 1/1 concluída |

A agenda está disparando, mas as duas últimas execuções falharam. Causa ainda não
diagnosticada; consultar condições e logs somente do Job/execução autorizado.
Não atribuir a falha ao bucket, token, IAM ou lock sem evidência. Sucesso de uma
execução não prova sozinho completude do SLA nem seu corte efetivo no BigQuery.

Nenhum recurso remoto foi alterado ao registrar este diagnóstico. A credencial
local não passou na verificação de identidade corporativa; operação remota depende
do Cloud Shell autorizado até a autenticação local ser corrigida.

## Diagnóstico posterior da execução de 21/09

Condições e logs fornecidos pelo usuário de `pipeline-orcamento-9d9kp`:
container iniciou; saída 1 (`NonZeroExitCode`). Às 09:02:33 UTC, o aplicativo
registrou RuntimeError `Já existe uma execução ativa para este board`.
O código gera esse erro quando a criação condicional de `sla_orcamento/writer.lock`
encontra objeto existente. Isso comprova bloqueio por trava, não que seu executor
esteja ainda vivo nem que a trava seja órfã. A causa da falha de 20/09 não foi consultada.

Próximo passo: ler proprietário/execution e geração da trava no bucket atual.
Antes de liberar: pausar exclusivamente `pipeline-orcamento-diario`, comprovar término
do proprietário e ausência de escritor concorrente; preservar evidência da trava.
Remover somente a geração comprovada pelo comando protegido do aplicativo,
reconciliar eventual pending com recover e validar Gold antes de retomar a agenda.
Não apagar control.json, checkpoints, reservas diárias ou arquivos do bucket.

Leitura posterior fornecida pelo usuário: trava criada em
`2026-09-20T09:01:49.525884+00:00`, execução `pipeline-orcamento-mxl5w`,
owner `7841b2aa535c4afd9074b36d6135f2e8`, geração `1789894909601392`.
Trata-se da execução de 20/09 marcada como falha na listagem. Confirmar suas
condições terminais e ausência de concorrência antes de liberar essa geração.
Nenhuma remoção de trava ou pausa de agenda foi comprovada até este registro.

## Confirmação posterior: agenda pausada e limite de memória

O usuário confirmou `Job has been paused` para `pipeline-orcamento-diario`.
Não retomar até concluir recuperação e validação; não há alteração de agenda LIA.
`pipeline-orcamento-mxl5w` tem completionTime `2026-09-20T09:05:02.774051Z`,
Completed=False e failedCount=1. Mensagem: `The configured memory limit was reached`.
Apesar do trecho exit code 0, a execução falhou por limite de memória segundo Cloud Run.
A cadeia causal observada é: encerramento por memória em 20/09, trava remanescente,
e recusa de execução por trava em 21/09. A existência de pending ainda deve ser verificada.

Verificar recursos realmente implantados e ausência de outras execuções não terminadas
antes de liberar a geração identificada. Aumentar memória é mitigação a validar com
medição de pico e investigação do consumo, não garantia de correção definitiva.
Persistir eventual alteração no deploy/infra para não regredir na próxima implantação.

## Preparação da recuperação

Consulta fornecida pelo usuário confirmou configuração remota: 1 CPU e 2 GiB.
Listagem sem filtro retornou 16 execuções, todas com runningCount=0 e completionTime.
O filtro anterior `NOT status.completionTime:*` falhou por interpretação de data;
não usar sua saída como evidência de ausência de execuções.
Com proprietário terminado e agenda pausada, a geração órfã identificada pode ser
liberada condicionalmente, sem outros disparos manuais concorrentes.

Deploy local ajustado para 1 CPU/4 GiB como mitigação inicial; alteração remota
ainda depende do comando no Cloud Shell. Medir pico na carga de validação.
Nome escolhido após autorização do usuário: `pipeline-monday`. Migrar job e alvo
da nossa agenda somente após recuperar/validar o estado; durante recuperação o
recurso ainda se chama `pipeline-orcamento`. Não criar dois escritores ativos.

Revisão do dimensionamento após pedido de mais folga para processamento e cruzamentos:
deploy local atualizado para 2 CPUs/8 GiB, com 5 testes de deployment aprovados.
Substitui a mitigação local anterior de 1 CPU/4 GiB; o remoto continua sem confirmação
de atualização. Monitorar consumo e custo; não é capacidade garantida para N produtos.
Recomendação de organização: família `pipeline-monday`, jobs por produto como
`pipeline-monday-sla-orcamento`; eventual coordenador pode usar `pipeline-monday`.
A nomenclatura do novo executor ainda não foi aplicada no GCP ou na agenda.

## Recuperação — atualização e unlock confirmados

Saída fornecida pelo usuário confirma atualização do job existente com
`--cpu=2 --memory=8Gi`. Execução `pipeline-orcamento-cl2ng` terminou com sucesso
após override de argumentos `unlock --lock-generation 1789894909601392 --execution-stopped`.
Essa operação remove somente a geração de trava indicada; não é uma carga de dados.
Agenda continua pausada. Ainda falta executar recover, validar a Gold e verificar
nova coleta e pico de memória. Nomes e bucket não foram migrados por essa operação.

## Recover e validação da Gold confirmados

Saída fornecida pelo usuário: `pipeline-orcamento-x5lsq` executou `recover` com
sucesso e `pipeline-orcamento-67899` executou `validate-gold` com sucesso.
Ainda não foram apresentados logs com contagens/corte; não inferir que houve nova
coleta ou consolidação das origens. Agenda permanece pausada.

Próxima sequência orientada: preservar cópia BQ da tabela atual sem sobrescrita,
criar recibo de backup-state (referencia gerações GCS; não é cópia independente
dos objetos), e testar daily manualmente com 2 CPUs/8 GiB. Verificar logs: sucesso
do container pode significar daily ignorado por reserva diária, não nova publicação.
Nenhuma dessas três etapas foi confirmada até este registro. Cópia operacional
de recuperação não é uma quinta tabela de consumo e não deve alimentar KPIs.

## Backup e execução manual confirmados

Saída fornecida pelo usuário confirma cópia de `viu_agenciamento.sla_orcamento`
para `viu_agenciamento.backup_sla_orcamento_pre_migracao_20260921` pelo job
`bqjob_r3a0bf05ef700bb61_000001a0c626a89f_1`, concluído com sucesso.
`pipeline-orcamento-4d67k` concluiu backup-state e `pipeline-orcamento-62flj`
concluiu daily. Falta obter URI do recibo e eventos da aplicação (publicação ou
skipped), contagens e corte. Exit 0 sozinho não comprova nova carga nem consumo
adequado de memória durante coleta. A agenda ainda está pausada e não houve
confirmação de migração de nomes, bucket ou publicação de SLA unificada.
