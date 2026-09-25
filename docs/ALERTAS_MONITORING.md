# Alertas externos do pipeline Monday

Estado posterior em 25/09: politica criada e verificada pelo operador apos
liberacao de acesso: alertPolicies/14344268581677879515 no projeto PRD.
Canais originais: 13521791824308717423 e 13521791824308717798.
Teste escrito e2cc0722-4759-4e31-ba58-39d01528a41d; confirmar entrega individual.
Usuario solicitou adicionar gustavo.siano@viu.com.br, mantendo Caio e Cristina.
Script atualizado/testado localmente; inclusao do terceiro canal no GCP pendente.
Nao precisa de imagem nova nem SMTP.

## Aplicacao serial no Cloud Shell

Enviar scripts/configure_monitoring_cloudshell.py para /home/caio_barroso/.
Executar primeiro `python3 /home/caio_barroso/configure_monitoring_cloudshell.py plan`.
Conferir tres destinatarios: caio.barroso@viu.com.br, cristina.andrade@viu.com.br
e gustavo.siano@viu.com.br. Para politica original, plan deve indicar um canal
a criar, policy_to_create=false e policy_channels_to_update=true.
apply altera apenas notificationChannels por PATCH, apos conferir a politica
original inteira; nao sobrescreve filtros, condicoes, documentacao ou estrategia.
Requer monitoring.alertPolicies.update. Se falhar, nao ampliar IAM automaticamente.
Depois executar o mesmo arquivo com `apply`; exigir configured_verified.
Aguardar alguns minutos para propagacao e executar com `test`.
Exigir recebimento pelos TRES destinatarios (verificar spam/quarentena).
`test_log_written` confirma somente escrita do teste, nao entrega de e-mail.

Script lista canais/politicas, cria somente recursos dedicados com identificacao
monday-alerts-v1 e verifica por GET. Reexecucao serial reutiliza configuracao exata;
colisoes, duplicatas ou divergencias param sem sobrescrever, exceto a adicao
expressamente autorizada do terceiro destinatario. Nao executar duas
instancias simultaneamente. Falha parcial pode deixar canais criados; consultar
plan antes de repetir. Nao altera IAM, API habilitada, tabelas, agenda ou LIA.
Autenticacao usa gcloud com token em memoria; nao grava token, .env ou senha.

## Cobertura e limites

- Falhas registradas pelo Cloud Run Job pipeline-monday em us-central1,
  incluindo orchestration_end failed/partial e workers com falha.
- Erros registrados pelo Scheduler pipeline-monday-diario em us-central1.
- Teste explicito em log separado pipeline-monday-alert-test, recurso global,
  evento notification_test; nao simula falha nos logs reais do job.
- Rate limit 15 minutos e fechamento automatico apos 30 minutos sem novos logs.
  Fechar incidente nao comprova recuperacao. Confirmar publicacao/controle/dados.
- Nao detecta silencio total, agenda pausada, dados antigos sem log de erro,
  nem valida semantica de dados. Validacoes internas e conferencia da proxima
  execucao continuam necessarias. Nao garante um e-mail por erro individual.
- Logs excluidos podem nao disparar alerta. Teste depende de propagacao,
  incidente ja aberto, rate limit e entrega corporativa.
- SMTP interno continua sem configuracao: delivery=not_configured descreve SMTP,
  nao o canal independente do Monitoring. Nao declarar SMTP homologado.

Se HTTP403, pedir ao administrador permissoes de listar/criar/consultar canais
e politicas do Monitoring e logging.notificationRules.create; teste precisa de
logging.logEntries.create. Nao conceder Owner/Editor nem alterar contas da LIA.
Se API desabilitada, solicitar habilitacao ao responsavel; script nao a habilita.
Credenciais anteriormente compartilhadas devem ser rotacionadas; nao reutilizar.

Para reverter, desabilitar apenas a politica cujo nome de recurso foi retornado
no recibo, via Monitoring. Nao remover canais compartilhados ou outras politicas.

Referencia: https://docs.cloud.google.com/logging/docs/alerting/log-based-alerts
