# Entrega candidata v18 — ciclos continuos

Estado: codigo integrado e testes locais; NAO implantado. Producao v17 preservada
ate migracao explicita. O ensaio recebido pelo operador teve 2.183 projetos,
9.617 passagens, 1.583 candidatos, 600 excluidos sem Entrada inicial, 1.685 ciclos
(1.346 entregues, 92 em andamento, 247 interrompidos), 1.211 entregas observadas,
221 passagens estimadas e 32 ciclos com estimativa. Isso NAO e recibo de publicacao.
Contagens podem mudar: v18 tambem reconhece idade aberta quando comprovada na
Gold Globocorp no mesmo corte, mesmo item/passagem, calendario, sem divergencia.

Verificacao local final: 621 testes aprovados, 3 ignorados; Ruff nos arquivos
alterados sem erros. Pacote runtime/pipeline-monday-release-20260925-v18-ciclos.zip,
107 arquivos fonte, SHA256:
ad9a802572c5bb9b13140cf6018a90fe345cbbfcf6c8a4bf98ee80815eedfdbb.
Nenhum segredo ou dado privado no pacote. Imagem, inicializacao, publicacao e
execucao automatica v18 ainda dependem de recibos GCP; testes nao os substituem.

## O que muda

Quatro tabelas publicadas juntas em uma transacao BigQuery:

| Tabela | Grao | Chave / uso |
|---|---|---|
| monday_sla_orcamento | passagem | interval_id; trajetoria e tempos por categoria |
| monday_ciclos_orcamento | ciclo | ciclo_id; entrega, reabertura ou andamento |
| monday_fila_precificacao | projeto | projeto_id; recorte Entrada isolada, confirmado no cadastro |
| monday_sla_baixa_qualidade_de_dado | projeto | projeto_id; motivos e evidencias para investigar |

SLA inclui projetos em Entrada. Fila e subconjunto; NAO somar fila+SLA.
Qualidade e diagnostico: pode coexistir com SLA quando ha trecho utilizavel.
Ausencia de Entrada inicial ou prefixo nulo sobreposto exclui projeto da principal.
Outros problemas deixam trechos/ciclos nao mensuraveis explicitos, sem apagar
evidencias. Fonte sem mapa e filtros anteriores continuam fora da populacao.
Todos os calculos sao refeitos diariamente: corrigir cadastro pode reincluir item.

Relacionar ciclos.ciclo_id (1) a SLA.ciclo_id (N), filtro unidirecional.
Nao juntar as duas tabelas por projeto_id para somar ciclos: multiplicaria totais.
interval_id_inicio/fim referenciam passagens do ciclo; fim nulo se aberto.
projeto_id e comum; item_id_viu2/globocorp sao IDs nativos separados por ambiente.
Marca, talento, interveniencia, equipes e tipos continuam em cadastro_atual_* da
principal; para segmentar ciclos use uma linha por projeto, conforme consultas.
Cadastro atual nao comprova responsavel ou marca no momento historico da passagem.

## Colunas para consumo

Na principal: ciclo_id, sla_categoria_tempo, sla_grupo_permanencia_id,
sla_continuacao_mesmo_status, sla_retorno_status, sla_origem_duracao,
sla_referencia_ate_utc, sla_saida_estimada_utc, sla_horas_corridas,
sla_horas_uteis, sla_motivos_json, sla_versao_regra.
As novas colunas fisicamente nullable permitem migracao aditiva; o validador
recalcula e verifica integralmente antes de cada publicacao.

Categorias: operacao (inclui Entrada/revisao), feedback, terceiros, standby,
terminal, desconhecido. Filtrar categoria antes de somar horas. Horas de espera
NAO sao SLA operacional. Idade aberta NAO e entrega concluida.
origem_duracao: observada, estimada_migracao, idade_aberta_no_corte, indisponivel,
nao_operacional_terminal, prefixo_nulo. NULL nao e zero.
Mesmo status continuando na migracao compartilha grupo_permanencia_id; usar
COUNT DISTINCT desse campo para permanencias, nao COUNT(*) de passagens brutas.

Nos ciclos: operacao_horas_* (sem espera externa), terceiros_horas_*, standby_horas_*;
situacao entregue/em_andamento/interrompido; tipo_ciclo primeira_elaboracao ou
revisao_reabertura; duracao_completa; contem_estimativa; contem_idade_aberta;
kpi_entrega_observada. Feedback apos entrega e analisado nas passagens.
Para indicador estritamente observado filtrar kpi_entrega_observada=TRUE.
Para analise com estimativas filtrar duracao_completa e mostrar contem_estimativa.
Sem evidencia de tempo completo, totais ficam NULL, mesmo com situacao entregue.

Campos antigos ciclo_precificacao_id, entrega_precificacao_observada,
precificacao_*, papel_precificacao e situacao_ciclo_precificacao continuam como
compatibilidade historica da v9, NAO descrevem ciclos continuos v18. Novos paineis
usam monday_ciclos_orcamento e ciclo_id. versao_contrato v9 permanece linhagem;
sla_versao_regra identifica projecao nova e journal usa destinos-ciclos-v2.
Nao misturar duracao_analise_* legada com sla_horas_* em um mesmo indicador.

## Publicacao, migracao e falhas

Novos schema_ciclos_v18.json nas pastas das quatro tabelas. Nao executar DDL
manualmente. Inicializador cria somente ciclos e adiciona colunas nullable ao
SLA, preservando dados anteriores. Novo journal privado:
consolidado/diario/cycles-destinations-control.json. O journal v17 e os artefatos
anteriores ficam preservados. IAM permanece restrito ao pipeline, sem tocar LIA.
As quatro cargas sao DELETE+INSERT dentro da mesma transacao; nenhuma pode
ficar publicada sozinha. Temporarias de query nao sao tabelas permanentes extras.
Timeout conserva pending e recupera mesmo job_id; erro definitivo da transacao
preserva o lote anterior. Nao apagar lock, journal ou tabela para destravar.

1. Upload ZIP v18, conferir SHA256 e fazer build --async (nao pausa agenda).
2. Conferir SUCCESS e digest da imagem; nao usar tag mutavel no deploy.
3. Pausar somente pipeline-monday-diario; conferir nenhuma execucao ativa.
   Antes de migrar, executar imagem nova com args cycles-plan,--manifest,/app/pipelines.json.
   Exigir cycles_bundle_plan_verified (sem escrita); se falhar nao inicializar.
4. Atualizar pipeline-monday para digest v18, comando pipeline-monday,
   args initialize-cycles,--manifest,/app/pipelines.json,--writers-stopped.
5. Executar --wait; conferir destinations_initialized/status cycles_initialized.
6. Restaurar args daily,--manifest,/app/pipelines.json e executar --wait.
7. Conferir orchestration_end, consolidated_publication_confirmed, destinos,
   publication_verified=true e nenhum ERROR para essa execucao.
8. Rodar consultas de VALIDACAO_E_ANALISE_CICLOS_V18.md. Conferir pending=null,
   initializing=false, contract=destinos-ciclos-v2 no journal novo.
9. Retomar scheduler e confirmar ENABLED, 0 6 * * *, America/Sao_Paulo.
10. Confirmar proxima execucao automatica e recebimento de alertas se houver falha.

Depois de initialize-cycles, NAO voltar imagem v17 simplesmente: schema mudou.
Se inicializacao interromper, repetir inicializador v18 com escritores parados.
Se daily falhar, manter imagem v18, investigar log e pendencia; a recuperacao e
automatica na proxima tentativa. Restauracao v17 requer plano proprio com
artefatos preservados e verificacao dos tres destinos; nao prometemos rollback
automatico por troca de imagem. Antes da migracao, v17 segue operando normalmente.

## Aceite

Nenhuma chave duplicada/nula, ciclos orfaos, fim antes de inicio ou tempos negativos;
horas uteis <= corridas; ciclo observado nao estimado; queue subset; projetos
aceitos+excluidos reconciliados pelo report (nao somar qualidade com principal).
Conferir amostras reais interambiente e reabertura, nao apenas contagens. Ainda
nao homologar indicadores v18 antes de verificar os resultados da carga real.
