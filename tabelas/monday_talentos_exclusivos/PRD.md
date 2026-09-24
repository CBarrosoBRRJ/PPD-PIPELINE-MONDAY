# Talentos — candidato não implantado

Origem: board 18429499631, incluindo grupos exclusivos, não exclusivos e finalizados.
O nome da tabela não implica filtro de exclusividade. Todas as páginas de itens
retornadas, sem aplicar filtro da view. Subitems, arquivados/lixeira não estão
implicitamente incluídos. Grão: board_id + item_id, estado atual observado.

Mesma política diária, schema base e protocolo de publicação descritos no
[backlog](../monday_backlog_agenciamento_2026/PRD.md). SPEC versionado no pacote
define os IDs/tipos confirmados. Status e vínculo são atributos distintos. O rótulo
com codificação divergente é preservado, não fundido silenciosamente com outro.

Nome artístico, status, vínculo e pessoas das equipes são atributos atuais. Pessoas
multivalor em JSON STRING, preservando ID/tipo; nomes não disponíveis ficam NULL.
Sem join por similaridade de nomes com talentos do backlog. Marca/correspondência
entre produtos requer identidade explícita. Consumidores: gestão do cadastro e
distribuição atual de carteira, não produtividade histórica individual.

Falhas de coleta/schema preservam a publicação anterior e sinalizam falha do produto;
produtos independentes podem continuar. Captura completa válida substitui a tabela
de consumo para refletir edições, inclusões e remoções do escopo. Gerações privadas
preservam auditoria, não constituem tabela histórica pública. Não implantado.
