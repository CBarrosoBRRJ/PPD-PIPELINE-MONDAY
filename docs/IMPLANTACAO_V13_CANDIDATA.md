# Implantação candidata v13 — não executada automaticamente

Referência funcional: [PROJETO_EXPLICADO.md](PROJETO_EXPLICADO.md).
Código local/CI não é homologação de produção. Última versão GCP confirmada: v12/v7.
Não alterar recursos LIA, Terraform legado ou credenciais compartilhadas.

## Evidência local do pacote

- 511 testes passaram; 3 testes de integração foram ignorados no ambiente local.
- Ruff e git diff --check aprovados para as alterações.
- Pacote source-only: `runtime/pipeline-monday-release-20260924-v13.zip`, 98 arquivos
  de código/configuração de build mais inventário de hashes, sem .env/dados privados.
- SHA256: `51342d614d38467314c36100bcf0fcd35f285a6e640e64ff58730d4e2b061f16`.
- Build, ensaio real, migração, tabelas, agenda e alerta externo permanecem pendentes
  de recibos do GCP. Não afirmar homologia local/produção a partir desse teste.

## Portões de liberação

1. Testes, Ruff, contrato/DDL gerados e revisão do inventário source-only do ZIP.
2. Operador envia ZIP ao Cloud Shell, confere SHA256 e extrai em diretório exclusivo.
3. Executa `python3 migrate_pricing_contract.py plan`: somente leitura, registra
   geração/fingerprint atuais do controle. Não reutilizar valores de ontem.
4. Cloud Build gera imagem com o Dockerfile do pacote; registrar digest sha256
   (não basta tag). Nenhuma agenda/tabela muda ao construir a imagem.
5. Registrar configuração atual do job em arquivo privado. Pausar apenas
   pipeline-monday-diario, conferir ausência de execução ativa. Atualizar o job
   para imagem candidata por digest, comando pipeline-monday e argumentos
   `snapshot-check,--manifest,/app/pipelines.json`. Executar e conferir os dois
   produtos `validated` com contagens reais. Esta operação lê Monday, sem escrever
   BQ/GCS/e-mails. É ensaio real, não apenas plano de manifesto.
6. Após aprovação, mudar os argumentos para `plan,--manifest,/app/pipelines.json`.
   Rodar novo plano e revisar identidade. Aplicar `migrate_pricing_contract.py apply`
   com `--expected-generation`, `--expected-fingerprint`, `--expected-image` atuais.
   Script exige agenda pausada, imagem fixada, modo plan e ausência de execução.
7. Mudar argumentos para `daily,--manifest,/app/pipelines.json`; executar com --wait.
   Conferir quatro produtos, schemas, contagens, fingerprints e controles sem pending.
8. Validar cobertura/casos reais de precificação, cadastro atual e ausência de
   regressão dos campos antigos. Totais não se repetem fora da linha de entrega.
9. Configurar canal de alerta com credenciais rotacionadas em Secret Manager e
   endpoint corporativo autorizado. Teste de recebimento deve ser acordado com os
   destinatários; nenhum e-mail de teste real foi enviado pelo desenvolvimento.
10. Retomar apenas a agenda do pipeline e verificar execução automática seguinte.

Não declarar os passos 5–10 feitos sem recibos do ambiente.

## Falha e recuperação

Antes da migração de controle, o ensaio snapshot-check não altera tabelas/controle;
pode retornar à imagem v12 e argumentos daily previamente registrados. Conferir
configuração antes de retomar agenda.

Depois da migração, manter agenda pausada se houver erro. Não voltar somente a
imagem: v12 não reconhece controle v8. Inspecionar journal/pending/locks e recuperar
com a imagem compatível. Rollback do contrato/tabela exige procedimento revisado,
geração exata e artefatos anteriores verificados; não apagar controles ou locks.
Uma falha de produto pode coexistir com sucesso de outro produto independente.
O coordenador informa falha geral; não repetir primeira carga manualmente.

## Limitações conhecidas

- Arquivados/lixeira e subitems não são automaticamente enumerados pelas cargas.
- Snapshots não são transações da API; coletam durante uma janela de leitura.
- Esvaziamento total do board requer revisão antes de apagar a publicação anterior.
- Não existe garantia de esforço histórico por pessoa nem continuidade entre contas.
- SMTP sem configuração registra not_configured; não há alerta externo homologado.
- Acesso GCP local foi negado; implantação depende do Cloud Shell autorizado.
