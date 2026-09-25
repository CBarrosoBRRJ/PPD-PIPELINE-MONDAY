# Baixa qualidade de rastreabilidade — candidato v17

Uma linha por projeto da população selecionada da consolidação que não atende
ao recorte de sequência ou apresenta Entrada isolada divergente do cadastro atual.
Chave projeto_id preservada. Não inclui automaticamente projetos sem mapa nem
exclusões anteriores de título/Input/talento. Não representa todos os problemas
do board. Contrato físico em docs/schema.json, gerado do schema executável.

motivos_json contém lista de motivos; um projeto pode ter vários. Não somar
contadores de motivos para contar projetos. evidencias_passagens_json contém
IDs, origem, ordem, status e datas de TODAS as passagens do projeto selecionado.
quantidade_passagens registra o grão original; não é quantidade de projetos.
Cadastro atual é explícito em cadastro_atual_json e captura; não comprova autoria.

Ausência de Entrada, lacunas, status desconhecido após Entrada, fronteira entre
ambientes não homologada e divergência de fila são motivos distintos. Não imputar
culpa à equipe. Entrada → Feedback diretamente observada é permitida. Não exigir
Entrada no dia de criação. Correções são reavaliadas diariamente; projeto pode
mudar de destino. Falta técnica de cadastro bloqueia, não vira exclusão de negócio.

Publicação conjunta transacional com SLA/fila, sem alteração das fontes.
Estado: implementação local; ainda não criada/homologada no GCP.
