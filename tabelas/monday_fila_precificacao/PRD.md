# Fila de precificação — candidato v17

Uma linha por projeto selecionado no consolidado que tenha somente Entrada como
status conhecido, sem saída observada, e cadastro atual também Entrada. Não é a
fila completa do board: itens sem mapa e fora do escopo anterior não participam.
Chave projeto_id preservada. Esquema em docs/schema.json; campos obrigatórios
e tipos são gerados do contrato Python compartilhado com o publicador.

Espera desde o evento Entrada até cadastro_capturado_em. Horas corridas e úteis
com calendário seg-sex 10–13/14–19, São Paulo, BR PUBLIC. Não é esforço da equipe
nem prazo de entrega. Espera zero é possível; desconhecido não vira zero.
Marca/talento/cadastro são atuais, não atribuições históricas. JSON mantém equipes
e demais atributos já disponíveis no backlog. Prefixos de status nulo são tolerados
como evidência, não como etapa de trabalho.

Reclassificação diária junto do SLA e baixa qualidade, sem denylist. Falha técnica
interrompe o lote. Publicação dos conteúdos em transação conjunta; criação inicial
separada e controlada. GCS mantém artefatos e journal para recuperação.
Estado: implementação local; ainda não criada/homologada no GCP.
