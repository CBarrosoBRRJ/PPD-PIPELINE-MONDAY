# Auditoria offline de cobertura por item — 22/09/2026

687 arquivos verificados; 133.611 eventos únicos; 4.368 itens no contexto capturado.
Nenhuma alteração no GCP/Monday ou nos arquivos originais. Relatório privado:
`runtime/validation/viu2_reconciliation_20260922_v2.json` (fora do Git).

460 eventos em lote da coluna status_19: 383 contêm índice explícito e 77 não
contêm o campo value. Campo ausente NÃO prova limpeza do status.

| Referências lote/item | Quantidade | Interpretação limitada |
|---|---:|---|
| Mesmo UUID de ação, item e status em evento individual | 1.252 | Correspondência encontrada; não somar os dois registros |
| Sem evento individual, mas índice no lote | 357 | Evidência candidata, sem transição derivada nesta auditoria |
| Evento individual presente, lote sem índice | 222 | Preservar evidência individual; não completar payload bruto |
| Sem evento individual e sem índice no lote | 48 | Lacuna de valor a investigar |

As 48 referências sem índice/individual envolvem 36 itens distintos, todos
presentes no contexto capturado. As 357 referências com índice/sem individual
envolvem 277 itens (259 no contexto, 18 fora). Categorias se sobrepõem por item:
290 itens distintos possuem alguma referência sem contraparte individual;
272 estão no contexto. Não somar 277 + 36 como projetos únicos.

14 testes históricos passaram. A auditoria não valida durações, significado de
limpeza, correspondência entre contas ou corte oficial. Status: publicação bloqueada.
Não substituir desconhecidos por zero, índice vazio ou estado atual do cadastro.

Próximos passos: identificar semântica dos lotes por evidência, investigar os 36
itens com lacuna de valor (registro individual/UI/exportação da fonte, se disponível),
reconstruir transições com proveniência e deduplicação, confirmar horário de corte.
Mesmo após isso, a consolidação exige mapa revisado entre IDs das contas.

## Conferência autenticada complementar

Token lido da chave privada TOKEN_MONDAY_VIU2, sem impressão. Conta 5890468
confirmada por consulta me.account.id. Fonte apenas consultada, sem mutations.
Consultados os 36 itens com lacunas nos dias UTC 15, 16 e 22/01/2026, com paginação
até vazio: 449 eventos únicos. Todos já constavam do resgate original com payload
idêntico: zero IDs novos e zero payloads alterados. As 48 lacunas de valor permanecem.
Isto valida essas janelas selecionadas, não certifica todos os eventos da vida do quadro.

Complemento em runtime/archives/viu2_complemento_20260922_v1, 15 arquivos,
com cópia independente em AppData/Local/PPD-PIPELINE-MONDAY/resgate-viu2 e comparação
SHA-256 de todos os arquivos. Não enviado ao GCP nesta etapa. Relatório privado:
runtime/validation/viu2_complemento_comparacao_20260922_v1.json.
Original e tabela publicada permanecem intactos. Não interpretar ausência de value
como status vazio apenas porque a consulta complementar reproduziu a ausência.

## Triagem privada por item de origem

`scripts/profile_item_review.py` gerou
`runtime/validation/viu2_item_review_20260922_v1.json` a partir do resgate verificado.
São 4.668 itens distintos na união do contexto com referências de status nos logs:

- 4.212 com eventos individuais e sem lote pendente nesta auditoria;
- 434 com alguma referência de lote exigindo revisão;
- 22 sem evento individual de status.

Há 4.368 itens no contexto capturado e 300 fora dele. Ausência do contexto não prova
exclusão, arquivamento ou inexistência: não descartar essas referências históricas.
Os grupos são exclusivos, mas as razões de revisão dentro de cada item se sobrepõem.
Os 434 não são 434 projetos necessariamente incorretos: incluem casos com evidência
individual em que o lote não informa valor. Nenhum grupo certifica histórico completo.

Contrato deste relatório privado: origem viu2, uma linha por conta/quadro/item;
IDs STRING, contagens inteiras, presença no contexto BOOL, motivos por categoria.
Não calcula durações, corte, junções entre contas ou elegibilidade de consumo.
Todos os registros mantêm `sla_approved=false`; falha de integridade bloqueia geração,
saída existente não é sobrescrita. Consumidor: revisão técnica, não BI ou ML.
18 testes históricos passaram, incluindo quatro testes novos de triagem; Ruff passou.
Nenhuma mudança no GCP nesta etapa. O complemento ZIP foi posteriormente preservado
no GCP e seu SHA256 remoto conferido, conforme docs/ESTADO_GCP_2026_09_22.md da raiz.

## Reconciliação candidata de observações de status

`scripts/build_observations.py` executado sobre o resgate verificado gerou
`runtime/validation/viu2_status_observations_20260922_v1.json` (privado, fora do Git).
Resultado: 17.869 observações candidatas, sendo 17.464 com registro individual,
357 derivadas de referências explícitas de lote sem registro individual e 48
referências de lote sem valor conhecido. As 1.474 referências de lote com
contraparte individual ficam associadas à mesma observação, preservando IDs de
ambos os registros; não são somadas como mudanças adicionais.

Contrato: uma observação por conta/quadro/item/UUID de ação; na ausência desse
UUID, por evento/item, sem deduplicação presumida por horário ou status. IDs e
índices são STRING; índice e horário podem ser NULL em conflito/desconhecimento;
linhagem é lista de IDs, tipo do evento, índice, horário e origem do timestamp.
Prioriza horário individual quando há contraparte; horários individuais divergentes
bloqueiam a escolha. Não substitui valor individual desconhecido por valor do lote.
Os arquivos brutos são preservados, e duplicatas/conflitos estruturais de entrada
bloqueiam o processamento. Não filtra itens pelo cadastro atual.

50 observações têm status desconhecido/conflitante (incluindo as 48 de lote).
4.631 não possuem UUID de ação: permanecem separadas pelo ID nativo, com aviso;
isso não significa que seus eventos individuais sejam inválidos. Outros 28 eventos
de status não são mudanças individuais/lotes e exigem revisão do esquema/rótulos.
Nenhuma duração ou correspondência entre contas calculada; nenhum corte assumido.
Todas as observações têm `sla_approved=false`; o gerador de SLA existente ainda não
consome este artefato. Não houve publicação/implantação GCP nesta etapa.

25 testes históricos passaram (sete novos para observações); Ruff passou. Próxima
etapa técnica: incorporar evidência reconciliada ao cálculo com interrupção explícita
de intervalos em lacunas, revisão de rótulos históricos e preservação dos itens sem
cadastro. Publicação segue condicionada à validação; não anunciar entrega completa.

## Candidato de passagens com interrupção por lacunas

`scripts/build_passages.py` consumiu o artefato de observações e gerou
`runtime/validation/viu2_passages_candidate_20260922_v1.json`, registrando SHA256
do arquivo de entrada e calendário/versão de horas úteis. Sem rede, sem escrita no
GCP, sem corte presumido e sem alteração de Bronze ou do pipeline diário.

Resultado: 4.646 itens de origem com observações; 17.486 passagens candidatas:
12.790 encerradas entre mudanças conhecidas, 4.646 sem saída observada e 50
interrompidas por lacuna. Existem 50 registros de lacuna. Os 22 itens do contexto
sem evidência individual/lote não recebem passagens fictícias neste artefato.

Grão privado: passagem observada por conta/quadro/item/índice de status, com
instante de entrada, possível saída e IDs dos eventos de suporte/fechamento.
Horas corridas e úteis são arredondadas a três casas como na projeção existente;
usam BusinessCalendar (BR PUBLIC, São Paulo, sem feriados extras nesta avaliação).
Saída e ambas as durações ficam NULL em lacuna ou ausência de saída. Repetições do
mesmo índice apoiam a passagem sem inventar retorno. Status simultâneos conflitantes
interrompem a sequência; horário não localizável bloqueia durações de todo o item.
Passagens posteriores à lacuna podem formar novos trechos, sem cobrir o intervalo
desconhecido. A contagem de visitas é apenas observada, não total histórico garantido.

O contrato é de rascunho privado, não o schema público completo: ainda não inclui
cadastro/atributos, rótulos históricos revisados ou correspondência entre contas.
Todos os registros mantêm `sla_approved=false`. As 12.790 durações são candidatas,
não métricas homologadas. Os 28 eventos de esquema permanecem para revisão.
31 testes históricos passaram; seis novos testam as passagens; Ruff passou.
Não publicar este JSON diretamente no BigQuery nem tratá-lo como SLA final.

## Enriquecimento de rótulos e cadastro

`scripts/enrich_passages.py` verificou novamente o resgate e gerou
`runtime/validation/viu2_passages_enriched_20260922_v1.json`, com SHA256 do candidato.
Das 17.486 passagens, 17.199 têm rótulo explícito em evento de início; 287 não têm
rótulo histórico comprovado nesse instante e mantêm status_nome NULL. Não preencher
pelo rótulo atual nem pelo rótulo de um evento posterior. Nenhuma passagem apresentou
mais de um rótulo nos eventos de suporte. Isso não prova ausência de renomeações no quadro.

434 passagens pertencem aos 300 itens sem cadastro no retrato: projeto_nome e
atributos ficam NULL, mantendo IDs de origem e eventos. As demais recebem nome,
Marca/Talento originais e referências de pessoas do snapshot, com
cadastro_referencia_utc e attribute_source=snapshot_at_capture; não são atributos
históricos nem entidades/identidades homologadas. Não usar esses atributos como
features históricas de ML sem controlar disponibilidade temporal.

5.385 passagens abrangem algum evento de esquema da coluna (inclusive passagens
sem saída). É apenas sinalização para revisão: não implica 5.385 mudanças de rótulo.
Todos os registros mantêm sla_approved=false; faltam regras de elegibilidade,
rótulos ausentes, mapa de identidade entre contas e compatibilidade de contrato.

Incompatibilidade comprovada no código de models/bq_consumption.py: o contrato
atual exige duração para toda linha observed e exatamente uma passagem aberta
por item. O histórico deve preservar entradas observadas com duração desconhecida
e interrupções intermediárias. Não mascarar isso preenchendo zero, saída ou corte
inventados. É necessária uma versão de contrato que distinga falta de saída,
lacuna e continuidade; não relaxar o validador do pipeline corrente silenciosamente.

35 testes históricos passaram (quatro novos de enriquecimento); Ruff passou.
Sem alteração de tabela, agenda, permissões ou recursos GCP nesta etapa.
