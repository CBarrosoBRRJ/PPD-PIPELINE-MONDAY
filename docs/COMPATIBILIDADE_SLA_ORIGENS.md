# Compatibilidade dos schemas publicados

Evidência: saída de bq show fornecida pelo operador, após carga histórica.
viu2: 17.486 linhas, lastModifiedTime=1790127403215, 30 campos.
globocorp: 4.237 linhas, lastModifiedTime=1790098997870, 39 campos.
Schema e quantidade não comprovam igualdade de significado nem integridade de
trajetória. Não usar UNION ALL SELECT * nem somar métricas de projeto repetidas.

## Regras para o adaptador unificado

| Informação | viu2 | globocorp | Tratamento necessário |
|---|---|---|---|
| Identidade | item_id/board_id, projeto_id NULL | item_id/board_id, sem projeto_id | Mapa privado selecionado, preservando IDs nativos |
| Status | status_index | status_id | Confirmar codificação antes de comparar códigos |
| Marca/Talento | marca_original/talento_original | marca_nome/talento_nome | Preservar originais; não declarar normalizados equivalentes |
| Responsável | Ausente no contrato publicado | responsavel_orcamento | NULL histórico, sem copiar responsável atual para passado |
| Datas | Entrada obrigatória; saída nullable | Entrada/saída nullable | Nunca preencher entrada desconhecida |
| Duração | NULL quando saída não comprovada | Pode acumular até corte em passagem aberta | Não somar nem fechar fronteira presumida |
| Retorno | retorno_observado | eh_retorno | Guardar referência de origem; retorno global exige trajetória reconciliada |
| Qualidade | situacao_passagem/qualidade_rotulo/pendencias_json | qualidade_historico/elegivel_comparacao | Qualidades não são sinônimas; conservar evidência |
| Corte | Sem corte_utc do processamento diário | corte_utc | Não atribuir corte globocorp ao retrato viu2 |
| SLA total | Ausente | tempo_desde_entrada_horas e úteis | Não propagar total de apenas uma origem como total consolidado |

Ambos têm interval_id, item_id, board_id, cadastro_referencia_utc e versão de
calendário. Chave de linhagem deve incluir ambiente/conta e interval_id, não apenas
item_id ou nome. Ordem consolidada não pode inventar posição temporal para entrada
NULL; representar essa falta de evidência explicitamente.

Antes de liberar o adaptador: testar contra registros reais do destino globocorp,
além dos testes sintéticos. A captura local de atividade Monday não substitui a
Gold publicada, que aplica corte D+1 e exclusões de negócio. Exportação somente
leitura da Gold preserva a fonte de fato consumida, sem usar eventos posteriores
ao corte do BQ. Nenhuma tabela ou agenda foi alterada nesta conferência.
