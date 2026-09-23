# Correção v6 — contexto indisponível por projeto

Execução remota pipeline-monday-lq7h7 falhou no build_gold antes de store.commit:
ValueError: Tipo de Input: projeto sem cadastro para avaliar escopo.
A v5 confundia falta de contexto individual com falha global de extração.

Na v6, snapshot ausente no instante de reconstrução, célula não recuperada ou
rótulo de Input não recuperável excluem o projeto inteiro do SLA globocorp.
Não tratar esses casos como vazio. Input comprovadamente vazio continua entrando.
Coluna ausente/ambígua no quadro e JSON inválido seguem bloqueando o lote.
O código específico input_contexto_nao_verificado usa a auditoria privada já
existente; não há nova tabela, nova lista exportada ou apagamento de histórico.
O resumo de regras inclui missing_item_context_policy=exclude_project_v1.
IDs, contratos públicos, prefixos GCS e política histórica escopo-sla-v3 preservados.

Validação local: 342 passed, 3 skipped; Ruff passou. Testes cobrem ausência de
snapshot, snapshot futuro, célula ausente, índice desconhecido e coluna global
ausente, além da preservação de Input vazio e das passagens técnicas originais.
Build Docker local não executado: daemon indisponível. Build/smoke test devem ser
feitos no Cloud Shell antes do push e da troca de imagem.

ZIP: runtime/pipeline-monday-release-20260923-v6-contexto.zip (74 arquivos + manifesto).
SHA256: 0590b6cc41ad3c974707228d99dcf9c19cfc8654a4bb9b7a6c3db915bcd4371e.
Nenhuma mudança remota feita pelo agente. Não sobrescreve v5.

Estado informado: agenda pausada; job v5 com comando sla-pipeline replay.
Não retomar agenda assim. Após nova imagem: replay, conferência de publicação,
restauração do coordenador, consolidação e verificação antes de reativar agenda.
IAM Storage já ampliado pelo operador apenas para os prefixos da consolidação
e fontes fixadas. BigQuery jobUser no projeto e WRITER no dataset confirmados.
SLA viu2 já migrado e conferido integralmente (14.761); não repetir essa migração.
