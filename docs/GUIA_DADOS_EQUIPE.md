# Dados Monday para KPIs e machine learning

## Situação atual — v11, 23/09/2026

A tabela de consumo é monday_sla_orcamento, contrato sla-consolidado-estimativas-v6.
KPI oficial por etapa: sla_etapa_horas_uteis, por ambiente/status. Estimativas:
duracao_estimada_horas_uteis, separadas e identificadas como hipótese. Trajetória:
projeto_id + ordem_etapa, não filtro por item_id nativo isolado.
Ver [guia de entrega atual](ENTREGA_CONSUMO_ATUAL.md). Os totais e limitações
conferidos estão no [recibo operacional](ESTADO_GCP_2026_09_23.md).

## Contexto histórico — 21/09/2026 (substituído pelo recibo acima)

O dataset `gglobo-viu-dados-hdg-prd.viu_agenciamento` contém, conforme evidência
fornecida pela equipe, `log_monday_viu2` e a versão existente de `sla_orcamento`.
O log histórico foi resgatado e reconciliado: 133.611 eventos e 687 arquivos no GCS.
Isso comprova a preservação do histórico disponível, não sua completude desde a origem.

**A trajetória integrada ainda não está homologada para KPIs completos ou treinamento.**
`sla_orcamento_viu2` e a consolidação entre contas ainda não foram publicadas.
A tabela corrente não foi apagada nem substituída. Não interpretar a presença das
duas tabelas atuais como conclusão da migração analítica.

Nomes finais aprovados: `sla_orcamento_viu2` para o histórico congelado,
`sla_orcamento_globocorp` para a origem nova e `sla_orcamento` para a trajetória
unificada oficial dos KPIs. Não haverá `sla_orcamento_consolidado`. A tabela
existente `sla_orcamento` ainda é a versão anterior, não a consolidação homologada.

## Camadas e público

- Evidência: logs originais e contexto no GCS; log estruturado no BigQuery.
  Uso de engenharia/auditoria; não calcular SLA diretamente de contagem de logs.
- Passagens: uma linha por visita de projeto a status. Retornar ao mesmo status
  gera nova passagem legítima, não duplicata. Mesmas regras de horas nas duas origens.
- Trajetória consolidada: projeto canônico com passagens e linhagem entre ambientes;
  será a base oficial para análise após homologação.
- Features e alvos ML: produtos próprios e versionados, derivados da trajetória,
  somente após definir previsão, instante de referência e horizonte do alvo.

O objetivo de ML ainda não está definido. Não gerar uma única tabela de features
genérica nem escolher alvo/modelo sem especificar a pergunta de negócio.

## Contrato da futura consolidação

Obrigatório documentar e validar antes de publicar:

- Identidade estável de projeto e correspondência revisada com conta/quadro/item nativos.
- Identidade da passagem e referência aos eventos que comprovam início e fim.
- Origem e instante do evento, instante da coleta e referência temporal do cadastro.
- Estado da correspondência: confirmado, pendente ou ambíguo.
- Cobertura: origem única, migração reconciliada ou lacuna na migração.
- Qualidade da passagem: observada ou inferida; duração desconhecida é NULL, nunca zero.
- Corte de processamento, versão das regras/calendário e identificador da publicação.

Esses requisitos ainda não são colunas implantadas. O contrato físico deverá ser
versionado e testado antes de alterar os consumidores.

## Regras para KPIs

- Contar projetos distintos pela identidade canônica, não por número de linhas nem
  somando quantidades de projetos dos dois ambientes. Sem mapa confirmado, divulgar
  totais separados por origem e a quantidade pendente de correspondência.
- Duração de passagem não é duração total do projeto. Métricas totais repetidas em
  cada passagem não devem ser somadas. Início total exige Entrada comprovada.
- Comparar durações encerradas com evidência consistente; apresentar à parte casos
  abertos, desconhecidos e excluídos. Publicar denominador, cobertura e exclusões.
- Separar horas corridas de úteis. Horas úteis: seg-sex 10–13h e 14–19h, Brasília,
  feriados BR PUBLIC e adicionais configurados; calendário versionado.
- Não chamar tempo observado de atraso: metas de SLA ainda não foram definidas.
- Não somar passagens das duas origens antes de tratar sobreposição/lacuna da migração.

## Regras para ML

- Definir instante da previsão (`t`) e usar somente informações disponíveis até `t`.
  Data de evento e data em que o dado ficou disponível são conceitos diferentes.
- O cadastro resgatado em 21/09 não comprova marca, responsável ou outros atributos
  em janeiro. Sem histórico temporal desses atributos, não usá-los como features
  de previsões retrospectivas anteriores à coleta.
- Preservar registro de disponibilidade histórica; o resgate tardio não prova quando
  uma informação estaria disponível ao sistema que será usado em produção.
- Não incluir status final, duração futura, data de conclusão ou atributos posteriores
  à previsão entre as features. O alvo pode depender do futuro, com janela explícita.
- Separar treino/validação/teste no tempo e impedir que o mesmo projeto, inclusive
  suas duas identidades Monday, apareça em conjuntos incompatíveis com a avaliação.
- Projetos abertos são casos censurados: não tratá-los como concluídos com duração zero
  nem excluí-los silenciosamente, pois isso pode enviesar o modelo.
- Versionar snapshot de treinamento, regras, features, alvo, corte e mapa de identidades.
  Uma Gold diária mutável não é, sozinha, um dataset de treinamento reproduzível.
- Minimizar dados pessoais; nomes de responsáveis e outros identificadores não são
  features por padrão. Acesso deve ser concedido por grupo/finalidade e mínimo privilégio.

## Critérios para liberar à equipe

1. Logs e contexto com contagens/hashes reconciliados.
2. Alterações individuais e em lote reconciliadas por item/evento, sem dupla contagem.
3. Correspondências de projetos e lacunas explicitamente medidas, sem vínculo por nome.
4. Passagens com chaves únicas, sequência temporal, duração consistente e origem rastreável.
5. Amostras verificadas de projetos antigos, novos e que atravessaram a migração.
6. Dicionário e exemplos de uso por grão, nulos e restrições; responsável pela homologação.
7. Carga histórica protegida de sobrescrita; rotina diária observada com controle de falhas
   e indicador de última atualização. A meta da corrente é 06h Brasília, D+1; evidenciar execução.
8. Backup/recuperação antes da substituição da Gold existente ou retirada de bucket.

Falha de integridade bloqueia publicação. Lacunas conhecidas não devem desaparecer:
podem ser disponibilizadas em base explicitamente qualificada, sem anunciar completude.

Ver [continuidade dos projetos](CONTINUIDADE_PROJETOS_MONDAY.md) e
[evidências do resgate](../tabelas/monday_sla_orcamento_viu2/docs/RESGATE_2026_09_21.md).
