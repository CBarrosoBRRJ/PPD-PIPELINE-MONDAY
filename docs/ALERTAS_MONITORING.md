# Alertas externos do pipeline Monday

Estado: dois canais criados pelo operador; politica nao criada (HTTP403).
Consulta de permissoes nao retornou logging.notificationRules.create, ja
solicitada pelo usuario ao administrador. Aplicacao e teste de entrega pendentes.
Ver docs/RETOMADA_2026_09_25.md. Nao precisa de imagem nova nem SMTP.

## Aplicacao serial no Cloud Shell

Enviar scripts/configure_monitoring_cloudshell.py para /home/caio_barroso/.
Executar primeiro `python3 /home/caio_barroso/configure_monitoring_cloudshell.py plan`.
Conferir dois destinatarios: caio.barroso@viu.com.br e cristina.andrade@viu.com.br.
Depois executar o mesmo arquivo com `apply`; exigir configured_verified.
Aguardar alguns minutos para propagacao e executar com `test`.
Exigir recebimento pelos DOIS destinatarios (verificar spam/quarentena).
`test_log_written` confirma somente escrita do teste, nao entrega de e-mail.

Script lista canais/politicas, cria somente recursos dedicados com identificacao
monday-alerts-v1 e verifica por GET. Reexecucao serial reutiliza configuracao exata;
colisoes, duplicatas ou divergencias param sem sobrescrever. Nao executar duas
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
