# Entrega de consumo — Monday SLA

## Liberado

Tabela: gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento.
Release v12 / contrato sla-consolidado-analise-v7. Cada linha é uma passagem
observada de um projeto selecionado pelo mapa e pelas regras de escopo.
Não representa toda a população comercial; não inferir cobertura universal.

| Uso | Campo/regra |
|---|---|
| KPI oficial por etapa | AVG(sla_etapa_horas_uteis), por ambiente_origem e status_nome |
| Denominador da média | COUNT(sla_etapa_horas_uteis), não COUNT(*) |
| Projetos no KPI | COUNT DISTINCT projeto_id condicionado ao KPI não nulo |
| Trajetória | Filtrar projeto_id ou item_id_globocorp; ORDER BY projeto_id, ordem_etapa |
| Qualidade por projeto | qualidade_trajetoria e limitacoes_trajetoria_json |
| Contar qualidade sem duplicação | Uma linha por projeto: eh_ultima_etapa_observada |
| Hipótese de permanência | duracao_estimada_horas_uteis, explicitamente separada do KPI |
| Análise unificada corrida/útil | duracao_analise_horas e duracao_analise_horas_uteis |
| Proveniência da duração unificada | origem_duracao_analise; informar quantidade/percentual estimado |

O indicador unificado inclui hipóteses: não equivale ao KPI estritamente observado.
Consulta de exemplo: tabelas/monday_sla_orcamento/sql/duracao_unificada.sql.

NULL não é zero. Status terminal não acumula SLA após a entrada. Última observação
não comprova estado atual. Estimativa não comprova ausência de etapas intermediárias.
Horas úteis: seg-sex 10–13 / 14–19, São Paulo, feriados BR PUBLIC e extras configurados.
Não há meta contratual de atraso nem medida de esforço/produtividade individual.

Consultas prontas em tabelas/monday_sla_orcamento/sql: kpi_consumo.sql,
trajetoria_projeto.sql, trajetoria_com_estimativas.sql e qualidade_projetos.sql.
SQL é executado no editor DBeaver/BigQuery ou passado ao comando bq query;
não colar SELECT/WHERE diretamente no Bash.

## Evidências e operação

Recebido do operador: 9.648 passagens, 2.209 projetos, 6.227 valores de KPI e
191 estimativas no corte 23/09/2026 03h UTC. Publicação e controles SQL confirmados.
Execução pipeline-monday-f9gbw. Agenda ENABLED às 06h São Paulo, diariamente.
Ainda falta observar a primeira execução automática v11 com corte do novo dia.
HTTP 200 do Scheduler isoladamente não comprova publicação: conferir execução
Cloud Run, orchestration_end e publication_verified, além do corte em BQ.

ViU2 é histórico congelado no GCS/BQ; não depende de acesso à antiga conta Monday.
Globocorp continua coletado. A consolidada é reconstruída e sua seleção pode mudar
com o escopo/current Gold. Preservar contexto, histórico, mapa, estado e controles GCS.
Não apagar locks; em falha investigar execução/journal e manter publicação anterior.
Recuperação: contrato e protocolo em tabelas/monday_sla_orcamento/src/monday_sla_orcamento/publication.py
e documentação de implantação v11. Não executar Terraform legado nem alterar LIA.

## Limites e fechamento

Não aprovados: SLA total entre contas, histórico integral de todo projeto e ML
genérico. ML exige definição de alvo, instante de previsão e separação temporal;
estimativa com informação futura não é feature retrospectiva disponível antes dela.

Documentação local atualizada. Git/GitHub ainda não publicado nesta entrega;
revisar reorganização ampla, segredos, artefatos privados e arquivos do editor antes
de commit. Não afirmar igualdade remota até confirmar commit e push.
Recibo da imagem e SHA do pacote em ENTREGA_V11_ESTIMATIVAS.md.
