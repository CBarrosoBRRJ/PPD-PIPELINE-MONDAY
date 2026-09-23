# Continuidade dos projetos na migração Monday

Decisão de 21/09/2026: a unidade de análise é o projeto completo, não a conta
Monday nem o dia de criação da cópia. Preservar evidências separadas por origem;
consolidar a trajetória analítica por uma identidade estável de projeto.

## Produtos e atualização

| Produto | Conteúdo | Atualização |
|---|---|---|
| log_monday_viu2 | Todos os eventos disponíveis resgatados da origem | Congelado; já publicado |
| sla_orcamento_viu2 | Passagens históricas da origem, mesmas regras de evidência | Uma carga validada; ainda não publicado |
| sla_orcamento_globocorp | Passagens do ambiente globocorp | Diária, fechamento D+1 às 06h Brasília; novo destino ainda não implantado |
| sla_orcamento | Trajetória por projeto, incluindo as duas origens; destino oficial dos KPIs | Derivação diária; consolidação ainda não implementada/publicada |

Nomenclatura aprovada pelo usuário em 21/09: `sla_orcamento` é o nome final da
base unificada. A tabela já existente com esse nome ainda contém a publicação
anterior; não anunciar que seus dados já estão consolidados. O nome intermediário
`sla_orcamento_consolidado` não será criado.

Antes de assumir o nome final, migrar o escritor globocorp e seu estado dedicado
para `sla_orcamento_globocorp`, validar a carga e preservar backup da tabela atual.
Não trocar apenas BQ_TABLE sobre um checkpoint existente: identidade, journal,
prefixo GCS e agenda precisam ser reconciliados. Não permitir dois escritores no
destino `sla_orcamento`. A configuração de deploy legada ainda não foi migrada.

O retrato viu2 nunca é recalculado pela agenda. A consolidação pode lê-lo diariamente
sem atualizá-lo. Não mover fisicamente eventos de uma origem para outra.

## Identidade e grão

Uma passagem é diferente de um projeto. O mesmo projeto legitimamente tem diversas
linhas de status e pode aparecer nos dois ambientes. Deduplicar por nome ou excluir
o projeto antigo inteiro destruiria sua história.

A correspondência privada no GCS deve registrar `projeto_id`, ambiente, conta,
quadro, item, evidência da migração e responsável/data da validação. A chave da
origem é `(ambiente, conta, quadro, item)`; cada chave só pode apontar para um projeto.
Os IDs/SKs nativos permanecem intactos. Preferir identificador de negócio persistido
ou mapa da migração fornecido pela TI. Nome igual é apenas candidato para revisão,
nunca prova suficiente. Correspondências ambíguas ficam pendentes e não são fundidas.

`projeto_id` será um identificador técnico estável, sem nome de cliente/pessoa ou
status embutido. Gerar UUID uma vez e persistir no mapa; não recalcular a identidade
a cada atualização. Uma chave nativa nunca pode apontar para dois projetos.
Por padrão, o mapa desta migração é um-para-um entre itens viu2 e globocorp;
divisões/fusões de projetos exigem revisão explícita, não junção automática.

O contrato privado está em `models/project_mapping.py`: valida origem, UUID,
unicidade da chave nativa, evidência, revisor e data com fuso. Somente registros
approved entram no índice de junção. Essa validação estrutural não comprova sozinha
a verdade da correspondência; não existe mapa populado/homologado neste momento.

### Inspeção de identidade em 21/09/2026

Consulta somente leitura: 4.368 itens preservados viu2 e 4.767 itens globocorp,
sem IDs nativos em comum. Coluna LIA - Chave Sync ausente no retrato viu2 e preenchida
em apenas 8 itens novos: não é chave de integração histórica disponível.
Link SF: 25 valores coincidentes únicos em cada origem. Link da pasta de orçamento:
2.251 valores coincidentes únicos em cada origem. Esses números não se somam, pois
os mesmos projetos podem aparecer em ambos. São candidatos, não vínculos aprovados:
o significado/unicidade de negócio e possíveis cópias de pasta exigem validação.
Não há cobertura comprovada para todos os projetos. Solicitar mapa de migração à TI
quando não houver identificador de negócio persistido e verificável.

Preservar as colunas de negócio anteriores (Projeto, Status, Entrada, Saída, horas
corridas/úteis, Marca, Talento, Responsável e Retorno), acrescentando identidade
integrada, origem e qualidade da migração no contrato versionado. A chave de linha
da passagem não é projeto_id: um projeto tem várias passagens. Recalcular ordem e
retornos na trajetória reconciliada, sem somar métricas de projeto repetidas.

A saída consolidada manterá projeto_id e a linhagem das passagens/eventos. Um evento
é identificado por origem + conta + event_id. Eventos de contas diferentes não são
duplicatas só porque têm o mesmo ID, status ou texto. Operações de cópia/importação
precisam ser reconhecidas por evidência antes de excluí-las como transições artificiais.

## Tempo e lacunas

Preservar todos os logs disponíveis. Não aplicar descarte global por uma meia-noite
suposta e não selecionar projetos pelo created_at do destino.

O e-mail informa madrugada de 03/09/2026, sem hora exata. O fuso confirmado é Brasília.
O limite efetivo precisa de validação; criação do quadro novo e último evento antigo
isoladamente não provam a passagem de responsabilidade entre ambientes.

Uma passagem aberta no viu2 não deve acumular tempo até hoje só porque o histórico
foi resgatado depois. Tampouco o instante de importação prova nova Entrada. Calcular
continuidade entre as origens somente após reconciliar projeto, ordem dos eventos,
status e evidência da transferência. Se isso não for comprovável, conservar as
passagens observadas e sinalizar lacuna de migração; duração desconhecida continua NULL.
Não somar cegamente as duas tabelas SLA: isso pode duplicar tempo na fronteira.

## Sequência segura de implantação

1. Preservar raw e validar integridade: concluído conforme recibo do Cloud Shell.
2. Reconciliar alterações em lote/individuais do viu2 e validar candidato histórico.
3. Obter/validar mapa dos projetos e evidências da fronteira no globocorp.
4. Validar contrato consolidado, lacunas e casos de projeto que atravessou a migração.
5. Fazer cópia de recuperação da tabela atual e inventário do estado GCS/Job/agenda.
6. Publicar histórico sem sobrescrita; substituir tabela corrente atomicamente após
   reconciliação; publicar consolidado com linhagem. Não executar DROP antecipado.
7. Verificar execução diária real e reconciliar objetos antes de retirar qualquer
   arquivo do bucket antigo. Estado Terraform não é estado dos pipelines.

O construtor `tabelas/monday_sla_orcamento_viu2/scripts/build_sla_candidate.py` é somente offline,
produz rascunho com bloqueios e não publica. Não confundir candidato com SLA homologado.
