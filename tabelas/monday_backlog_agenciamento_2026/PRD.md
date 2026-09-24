# Backlog agenciamento 2026 — candidato não implantado

Origem: board 18429499488, todas as páginas de itens retornadas pela API, sem
filtros da view ou do SLA. Não inclui implicitamente subitems/arquivados/lixeira.
Grão: estado observado por board_id + item_id, não histórico de movimentações.
Atualização diária por snapshot completo: inclusões, edições e remoções do escopo
da coleta se refletem no próximo sucesso; ausência não comprova exclusão versus
arquivamento. Não é snapshot transacional da API: captura ocorre durante a coleta.

Schema board-snapshot-v1: IDs INT64; item/grupo/estado e campos de negócio STRING;
cadastro/criação/captura TIMESTAMP. Pessoas e opções múltiplas em JSON STRING,
preservando IDs e cardinalidade. Nome ausente não inventado. Campos de negócio
podem ser NULL; ID e captura não. Responsáveis refletem cadastro atual, não autoria.
SPEC no pacote define IDs/tipos confirmados pelo operador em 24/09/2026.

Consumidores: painel de backlog e enriquecimento atual da consolidada via item_id
Globocorp, nunca join por nome. Não copiar atributos atuais sobre fatos ViU2 sem
marcar explicitamente a origem/data. Dados da LIA não são selecionados nem alterados.

Falha: schema/tipo obrigatório alterado, duplicidade, board vazio, paginação ou
contagem incompatível bloqueiam publicação. Board vazio exige revisão operacional.
Preservar anterior e sinalizar erro, sem eliminar linhas devido a falha de acesso.
Publicação candidata: NDJSON privado GCS, lock não expirável, journal com job ID,
load atômico BQ e fingerprint integral antes de promover active. Não implantar
sem teste de recuperação, revisão de permissões e reconciliação real.
