# Carga histórica com nome final — autorização posterior do usuário

O usuário solicitou a tabela com nome final antes de sua inspeção de negócio.
Esta autorização substitui a proposta de criar uma tabela com sufixo revisao;
não aprova dados para KPI/ML nem autoriza descartar lacunas.

Destino único: viu_agenciamento.monday_sla_orcamento_viu2. São 17.486 passagens
do viu2 no contrato sla-viu2-review-v1 (schema já validado), não eventos brutos e
não a trajetória consolidada. Mantêm-se NULLs, validacao_negocio=pendente,
elegivel_comparacao=false e projeto_id=NULL. O mapa selecionado está separado;
essa carga não o aplica silenciosamente nem exclui históricos não mapeados.

O export original permanece imutável, com sua proibição original de publicação.
O novo load_manifest.json registra a autorização restrita ao nome final e mantém
kpi_approved=false. Não houve alteração do contrato público globocorp.

Pacote: runtime/viu2-sla-bq-20260922-v1.zip. Executar publish_historical_sla.py
no Cloud Shell corporativo após upload e conferência SHA256. O script valida o
pacote, copia para prefixo histórico dedicado, compara tamanho/MD5 remoto e usa
job determinístico WRITE_EMPTY, schema explícito e zero registros inválidos.
Confirma schema e contagem da tabela, sem alegar comparação integral de conteúdo
remoto. Repetir reconcilia o mesmo job; não anexa registros nem sobrescreve tabela
não vazia. Não muda IAM, agendamentos, writer state, LIA ou tabelas existentes.

A tabela é congelada, sem carga diária. A rotina atual atualiza apenas globocorp.
Consolidado, rotina diária consolidada e limpeza dos legados continuam pendentes.
O pacote está preparado localmente; publicação exige recibo de execução GCP.
