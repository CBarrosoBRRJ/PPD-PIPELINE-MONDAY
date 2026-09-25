# Separação de consumo — candidato, não implantado

## Implementação posterior v17 (local)

Classificação integrada ao worker, contratos gerados nas pastas dos dois novos
produtos e publicador transacional implementados. Espera da fila usa calendário
versionado até captura do cadastro. Treze testes adicionais de projeção/publicação
passaram, inclusive falha, timeout, perda de confirmação e recuperação.
As pendências de implementação descritas no ensaio abaixo foram substituídas
por esta implementação candidata; implantação e homologação reais continuam pendentes.

Ativação exige initialize-destinations com escritores parados. Usa controle
separado destinations-control.json no MESMO prefixo/lock consolidado/diario.
Somente após essa inicialização daily utiliza a nova separação. Sem o controle,
o comportamento v16 permanece, evitando ativação acidental por simples troca de imagem.
Referência do ensaio real: 1.363 projetos/6.366 passagens SLA, 4 projetos de fila,
816 projetos de qualidade representando 3.224 passagens. Fontes dinâmicas podem mudar.

## Protocolo e recuperação

Inicialização confere a publicação v16, recusa adotar novas tabelas já existentes
sem journal e cria somente as duas tabelas novas vazias. Não usar essas tabelas
até primeira publicação conjunta confirmada. Se criação falhar, repetir inicialização
com a mesma imagem; não apagar controle ou tabelas. Inicialização incompleta bloqueia daily.

Cada rodada grava artefatos imutáveis por destino, hashes e relatório privado;
registra pending antes de submeter um único query job. Tabelas temporárias da
consulta materializam os artefatos; DELETE/INSERT nas três tabelas ocorrem dentro
de BEGIN/COMMIT TRANSACTION. Sem novas tabelas permanentes de staging. Schemas
e conteúdos são conferidos após commit antes de promover active por CAS no GCS.
Em falha terminal há rollback do DML; resultado incerto mantém pending e consulta
o mesmo job na recuperação. Não submeter novo candidato antes de resolver pending.
GCS e BQ não têm transação distribuída; o journal cobre perda de confirmação.

Após ativação, os scripts antigos que consultam control.json não verificam o
novo conjunto. Usar destinations-control.json/report do conjunto. O controle v16
é preservado como referência da transição, não atualizado como se ainda fosse ativo.
Não voltar à v16 isoladamente: sua verificação deve recusar a tabela filtrada.
Rollback exige procedimento explícito para as três tabelas e controles.

O SLA mantém schema/contrato físico v9; a regra da população e os novos produtos
são versionados destinos-projeto-v1 no controle/relatórios/novas tabelas.
Baixa qualidade armazena uma linha por projeto e evidências em JSON; fila uma
linha por projeto. Não comparar suas contagens de linhas com passagens do SLA.
Atualizar Power BI somente após receipt publication_verified=true do conjunto.

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
