# Migração de nome do SLA — preparação local

Destino: `viu_agenciamento.monday_sla_orcamento_globocorp`. Origem atual:
`viu_agenciamento.sla_orcamento`. Não é a consolidação viu2/globocorp.
Mesmo quadro globocorp, grão passagem por status, chave interval_id, schema público
v5 e regras existentes. Nenhuma alteração de datas, horas, NULLs ou elegibilidade.
Consumidores precisam mudar a referência após homologação.

`migration.rename_destination.rebind_destination` é uma função de manutenção
testada localmente; não está implantada na imagem v2.
O novo pacote oferece `rename-sla-plan --manifest /app/pipelines.json` e
`rename-sla-apply --manifest /app/pipelines.json --writers-stopped --expected-generation N`.
Plano exige uma cópia do destino já existente. Não cria nem sobrescreve tabelas.
Plano adquire/libera lock temporário, mas não altera control.json ou dados BQ.
Aplicação não verifica a agenda por API: o operador deve pausá-la e comprovar
ausência de execuções antes de declarar --writers-stopped. Não usar estes comandos
como argumentos padrão do job nem na agenda. Logs de falha omitem valores privados.
Não chamar daily com BQ_TABLE novo antes de migrar a identidade do controle.

Sequência obrigatória:
1. Preparar ferramenta e revisar dependências/consumidores antes da manutenção.
2. Pausar agenda pipeline-monday-diario; manter antiga pausada. Conferir término
   de todas as execuções dos dois jobs. Não alterar LIA.
3. Copiar tabela com WRITE_EMPTY/no_clobber. Preservar estado e tabela anteriores.
4. Plano sob lock: identidade antiga, pending ausente, checkpoint íntegro,
   fingerprint/schema de ambas as tabelas iguais ao recibo, destino sem expiração,
   tipo TABLE, localização e clustering compatíveis.
5. Aplicar somente com geração esperada e confirmação de escritores parados.
   Salvar/verificar backup imutável do controle; CAS troca apenas identity.table.
   Mantém active/publication/claims; job_id anterior é evidência histórica, não
   uma carga feita para o novo destino. Não apagar artefatos nem criar claims.
6. Atualizar BQ_TABLE do pipeline-monday; validar publicação e regras com a
   configuração nova antes de retomar agenda. O antigo passa a falhar por identidade,
   não deve ser executado ou ter a agenda reativada.
7. Remover nome antigo só após dependências migradas e nova publicação comprovada.

Não há transação entre controle e configuração Cloud Run. Se falhar após o CAS,
manter agendas pausadas e concluir configuração. Antes do CAS, a origem não muda.
Não restaurar controle antigo se houver carga nova: retorno exige reconciliação
da tabela e do estado atuais, nunca cópia cega do backup sobre dados recentes.
Backup do controle referencia objetos imutáveis; não substitui backup independente
dos objetos. Esta mudança não exclui buckets/jobs/tabelas nem chama a API Monday.
