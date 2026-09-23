# Contrato consolidado — sla-consolidado-analise-v7

Uma linha: passagem datada de origem preservada, ligada a projeto selecionado.
A ordem e a entrada são obrigatórias pela validação Python. Ausências não são preenchidas.
Schema independente do contrato globocorp e histórico; não alterar esses destinos.

| Campo | Tipo BQ | Obrigatório no schema |
|---|---|---|
| ordem_etapa | INTEGER | não |
| projeto_nome | STRING | não |
| status_nome | STRING | não |
| entrada_status_local | DATETIME | não |
| saida_status_local | DATETIME | não |
| duracao_horas | FLOAT | não |
| duracao_horas_uteis | FLOAT | não |
| marca_nome | STRING | não |
| talento_nome | STRING | não |
| responsavel_orcamento | STRING | não |
| marca_original | STRING | não |
| talento_original | STRING | não |
| eh_retorno | BOOLEAN | não |
| retorno_observado_origem | BOOLEAN | sim |
| projeto_id | STRING | sim |
| item_id | INTEGER | sim |
| board_id | INTEGER | sim |
| ambiente_origem | STRING | sim |
| conta_origem | STRING | sim |
| interval_id | STRING | sim |
| interval_id_origem | STRING | sim |
| item_id_viu2 | INTEGER | sim |
| item_id_globocorp | INTEGER | sim |
| ordem_origem | INTEGER | sim |
| status_index | STRING | sim |
| tipo_registro | STRING | sim |
| qualidade_historico_origem | STRING | sim |
| qualidade_identidade | STRING | sim |
| continuidade_validada | BOOLEAN | sim |
| elegivel_comparacao | BOOLEAN | sim |
| validacao_negocio | STRING | sim |
| entrada_status_utc | TIMESTAMP | não |
| saida_status_utc | TIMESTAMP | não |
| corte_globocorp_utc | TIMESTAMP | sim |
| cadastro_referencia_utc | TIMESTAMP | não |
| versao_contrato | STRING | sim |
| versao_calendario_origem | STRING | sim |
| pendencias_json | STRING | sim |
| registro_origem_json | STRING | sim |
| status_terminal | BOOLEAN | não |
| finalizacao_observada_utc | TIMESTAMP | não |
| situacao_sla_registro | STRING | sim |
| ciclo_observado_origem | INTEGER | sim |
| reabertura_comprovada_origem | BOOLEAN | sim |
| tempo_ciclo_observado_horas | FLOAT | não |
| sla_etapa_horas_uteis | FLOAT | não |
| classificacao_consumo | STRING | sim |
| motivos_inelegibilidade_kpi_json | STRING | sim |
| versao_regra_kpi | STRING | sim |
| quantidade_passagens_projeto | INTEGER | sim |
| qualidade_trajetoria | STRING | sim |
| limitacoes_trajetoria_json | STRING | sim |
| eh_ultima_etapa_observada | BOOLEAN | sim |
| versao_regra_trajetoria | STRING | sim |
| saida_estimada_utc | TIMESTAMP | não |
| saida_estimada_local | DATETIME | não |
| duracao_estimada_horas | FLOAT | não |
| duracao_estimada_horas_uteis | FLOAT | não |
| metodo_estimativa | STRING | sim |
| interval_id_referencia_estimativa | STRING | não |
| versao_regra_estimativa | STRING | sim |
| versao_calendario_estimativa | STRING | não |
| duracao_analise_horas | FLOAT | não |
| duracao_analise_horas_uteis | FLOAT | não |
| origem_duracao_analise | STRING | sim |
| versao_regra_duracao_analise | STRING | sim |

## Semântica de fechamento

status_terminal identifica o status daquela passagem, não o estado atual global do projeto.
finalizacao_observada_utc é a entrada no terminal; saída pode continuar NULL.
Durações de linhas terminais são NULL: não são tempo de SLA após encerramento.
registro_origem_json preserva inclusive a duração original, sem alterá-la na fonte.
ciclo_observado_origem é local a ambiente + projeto, não um ciclo completo entre contas.
reabertura_comprovada_origem exige saída anterior igual à próxima entrada na mesma origem.
tempo_ciclo_observado_horas só aparece no primeiro terminal de uma cadeia contínua
iniciada em Entrada comprovada na mesma origem. Não é o SLA vitalício consolidado.
Se houver lacuna, rótulo desconhecido ou sobreposição, não calcular o total dessa cadeia.
Encerrado e os dois Declinados são terminais atuais; Negócio Fechado exige configuração futura.

## Limitações de consumo

Contrato v7 preserva a elegibilidade por etapa da v4;
liberam apenas duração de passagem encerrada por ambiente + status, não total entre contas.
Demais linhas: nao_elegivel_etapa_origem_v1. Continuidade global permanece false.
Elegibilidade é recalculada na validação: calendário, evidência, pendências e durações.
sla_etapa_horas_uteis: FLOAT NULL fora do KPI; zero observado permanece zero.
AVG(sla_etapa_horas_uteis) usa apenas aprovadas; COUNT desse campo dá o denominador.
classificacao_consumo: aprovado_kpi_etapa, encerramento_observado, sem_saida_observada
ou evidencia_insuficiente. Não descreve necessariamente o estado atual do projeto.
motivos_inelegibilidade_kpi_json: lista dos bloqueios calculados, [] nas aprovadas.
versao_regra_kpi identifica a política aplicada automaticamente em cada execução.
Flags genéricas no JSON da origem preservam a revisão original, não anulam a aprovação local.
eh_retorno global é NULL; retorno_observado_origem conserva a informação de cada origem.
Marca/Talento originais viu2 não são apresentados como identidade de negócio normalizada.
A ausência de saída em não terminal não comprova abandono. Não envelhecer viu2 até hoje.
Sem Entrada comprovada, sem mapa, fora da Gold atual ou com ordem ambígua: fora da seleção.
Não usar total global nem treino ML homologado. Indicador cobre apenas população selecionada.
Falha de validação bloqueia carga. Diário usa WRITE_TRUNCATE atômico com schema explícito.
Leitura de contratos v2/v3/v4/v5/v6 permitida somente para reconciliação; candidato novo exige v7.

## Trajetória por projeto

quantidade_passagens_projeto: contagem das passagens publicadas por projeto_id; repetida nas linhas.
qualidade_trajetoria: historico_com_limitacoes ou sequencia_observada_sem_lacunas_detectadas.
Nenhuma dessas classes homologa completude vitalícia, SLA total ou treinamento ML.
limitacoes_trajetoria_json: lista de motivos do projeto inteiro, não só da passagem.
eh_ultima_etapa_observada: exatamente uma linha por projeto; não é prova do status atual.
versao_regra_trajetoria: auditoria-trajetoria-v1, calculada novamente em cada execução.
Para qualidade/cobertura de projetos, filtrar eh_ultima_etapa_observada; não somar contagens repetidas.
Para exibir histórico: ORDER BY projeto_id, ordem_etapa. Tabelas BQ não garantem ordem física.
Sem saída permanece NULL; a próxima entrada não fecha automaticamente uma lacuna.
Datas iguais em eventos diferentes não são ordenadas arbitrariamente; projeto ambíguo fica fora.

## Estimativa opcional de fronteira

saida_estimada_utc/local: próxima entrada Globocorp após passagem ViU2 não terminal sem saída.
Hipótese: permanência no status anterior até a próxima entrada observada, sem etapas intermediárias.
Não é saída observada, limite estatístico nem prova de continuidade entre contas.
duracao_estimada_horas/horas_uteis: calculadas desde a entrada anterior, arredondadas a 3 casas.
Calendário da estimativa identificado em versao_calendario_estimativa; sem aprovação de KPI.
metodo_estimativa: estimada_pela_proxima_etapa_entre_ambientes ou nao_aplicavel.
interval_id_referencia_estimativa identifica a passagem seguinte usada como hipótese.
versao_regra_estimativa identifica a política aplicada. Datas e durações estimadas são NULL
quando não aplicável. Não há coalescência com as métricas observadas/publicadas.
Bloqueios: terminal/desconhecido, saída existente, mesma origem/status, identidade inadequada,
sobreposição, ausência de próxima etapa ou próximo início posterior ao corte.
Não alimentar KPI oficial ou alvo ML com estimativa sem contrato analítico específico.

## Duração unificada para análise

duracao_analise_horas e duracao_analise_horas_uteis: prioridade à passagem observada validada;
caso contrário, estimativa autorizada de fronteira; demais NULL. Terminal não acumula.
origem_duracao_analise: observada_validada, estimada ou indisponivel; nunca ocultar a origem.
versao_regra_duracao_analise: duracao-analise-v1. Projeção revalidada em cada publicação.
Usar as duas medidas para análise unificada com hipóteses, mostrando participação estimada.
sla_etapa_horas_uteis mantém exclusivamente o KPI observado. Não mudou o calendário.
Não usar duração histórica reprovada só porque duracao_horas foi preservada na linhagem.
