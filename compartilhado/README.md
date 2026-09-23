# Regras comuns

Regras que afetam mais de uma tabela devem ter uma única implementação testada.
O pacote monday_comum implementa `escopo_sla.py`: títulos e Tipo de Input.
Os utilitários técnicos existentes continuam nos pacotes de origem, consumidos
por dependências explícitas; não foram duplicados aqui.

A política está em [REGRAS_ESCOPO_SLA](../docs/REGRAS_ESCOPO_SLA.md).
Vazios entram; ViU First e Proativo não. PACOTE só como prefixo do título.
Vazio precisa estar comprovado no cadastro; ausência de contexto histórico exclui
o projeto e seu par consolidado, conforme decisão explícita de 23/09/2026.
Não criar tabela de projetos excluídos ou novos backups no BQ por conta própria.
