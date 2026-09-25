# Separação de consumo — candidato, não implantado

Decisão do usuário: monday_sla_orcamento, monday_fila_precificacao e
monday_sla_baixa_qualidade_de_dado. Novos destinos autorizados, mas ainda não
criados. A v16 continua publicando a população anterior. Não declarar entrega
das três tabelas antes da implementação e homologação do publicador.

## Regras implementadas na auditoria

Classificação exclusiva por projeto, preservando todas as passagens de origem.
Entrada no dia seguinte à criação é permitida. Prefixo de status nulos ordenados
é tolerado e não vira trabalho/etapa sintética. Entrada → Feedback observada
diretamente não é defeito por si só. Projetos com etapa conhecida antes da Entrada,
lacuna, status desconhecido posterior ou fronteira não homologada vão para qualidade.

Somente uma etapa conhecida Entrada, aberta, com cadastro atual também Entrada:
fila. Se cadastro diz outro status, qualidade por divergência; não presumir fila
pela ausência de eventos. Projetos iniciados com cadeia coerente e em elaboração
ficam no SLA, mas sem tratar projeto aberto como entrega. Correções são reavaliadas
em cada classificação, sem denylist permanente.

Auditoria scripts/audit_destination_split_cloudshell.py depende do script
audit_project_start_cloudshell.py na mesma pasta. Ambos somente leem o artefato
ativo GCS, verificam checksum/contagem e controle estável. Sem alterações no cloud,
sem saída com nomes de pessoas/projetos. Contagens por destino e motivos apenas.

## Limites e próximo passo obrigatório

A classificação inicial cobre somente a população hoje consolidada. Não chamar
os projetos sem mapa de novos: podem ser migrados ainda não correlacionados.
O relatório distingue número de projetos e passagens; motivos podem se sobrepor.
Prefixos nulos são preservados no resultado privado, não devem gerar KPI.

Antes de trocar o escritor público: confirmar a distribuição real, definir
schemas/grão dos dois novos produtos (fila e qualidade em grão projeto), gerar
contratos e implementar journal/recuperação para o conjunto de três destinos.
O publicador atual é atômico para uma tabela, não para três; três cargas sucessivas
não constituem publicação conjunta atômica. Não adaptar o atual com DELETE manual
ou cargas sem controle. O cálculo de espera útil da fila deve reutilizar o calendário
versionado; ainda não implementado neste ensaio. Motivos de qualidade não implicam
culpa da equipe. Fontes intactas e exclusões de negócio anteriores preservadas.

Teste focado: 15 casos aprovados (início e separação), incluindo reclassificação,
fila divergente, fluxo direto e falhas técnicas. Execução real ainda pendente.
