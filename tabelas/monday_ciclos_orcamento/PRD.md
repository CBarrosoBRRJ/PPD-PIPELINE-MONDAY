# monday_ciclos_orcamento — candidato aprovado para implementacao

NAO PUBLICADO. Schema, motor e publicador de quatro tabelas integrados localmente
para release v18. Nao executar schema.sql isoladamente nem substituir imagem v17
pelo pacote de ensaio. Criacao aprovada pelo usuario em 25/09/2026.
Plano e mudancas de consumo: docs/ENTREGA_V18_CICLOS.md na raiz.

## Grao, origem e relacionamentos

Uma linha por tentativa continua de orcamento, desde Entrada ou reabertura
operacional ate Feedback, terminal ou corte (aberto). Derivada das passagens
consolidadas PRE filtro integral v17; nao soma fontes novamente nem cria identidade.
projeto_id liga os ciclos ao mesmo projeto na trajetoria. ciclo_id e UUIDv5 de
regra/projeto/passagem inicial: nao muda quando fecha. numero_ciclo e ordinal,
nao chave persistente. interval_id_inicio/fim referenciam passagens da trajetoria;
fim nulo para ciclo aberto. item_id_viu2/globocorp preservam IDs e origem.
Nao relacionar ciclos a passagens apenas por projeto_id: isso multiplica linhas.
Relacionamento futuro ciclos(ciclo_id) 1:N passagens(ciclo_id), filtro unidirecional.
Para segmentacao comum, dimensao projeto pode ser derivada por projeto_id unico;
nao criar relacao many-to-many entre fatos. Cadastro e atual, nao autoria historica.

## Regras e limites

Entrada obrigatoria como primeiro status conhecido do projeto, NULL anterior
permitido sem sobreposicao. Entrada repetida dentro do trabalho nao apaga ciclo.
Feedback fecha; proxima operacao reabre. Terceiros e Standby nao contam como
operacao nem criam ciclo sozinhos. Operacao inclui fila em Entrada e revisoes.
Mesmo status na migracao preserva grupo de permanencia; nao cria retorno/ciclo.
Trecho aberto ViU2 pode ser estimado ate a primeira passagem Globocorp apenas
com par selecionado consistente, cronologia crescente, status conhecidos e sem
sobreposicao. Datas observadas nao sao sobrescritas. Estimativa NAO e KPI observado.
Ausencia de movimento nao comprova que nada aconteceu no intervalo migrado.

Campos de horas uteis usam calendario do projeto (seg-sex 10-13/14-19 Sao Paulo,
feriados BR PUBLIC e extras). Desconhecido permanece NULL, nao zero. Idade aberta
exige prova do estado no corte, nao um cadastro posterior; integracao dessa prova
usa a Gold Globocorp observada, aberta, sem divergencia, mesmo corte/calendario/ID.
Sem essa prova produz NULL. Nao calcular ate NOW().

operacao_* exclui terceiros/standby; terceiros_* e standby_* sao tempos separados
internos ao ciclo. Feedback apos entrega fica na trajetoria para analise de espera,
nao no ciclo encerrado. Quantidade de linhas/ciclos nao e numero de projetos.
duracao_completa indica calculo sem trecho desconhecido, podendo conter estimativa;
contem_estimativa deve acompanhar qualquer media/percentil. kpi_entrega_observada
exige ciclo entregue, sem estimativas/idade aberta ou fronteira nao homologada.
Um ciclo valido nao aprova automaticamente a historia inteira do projeto.

## Contrato executavel e publicacao futura

Campos/tipos/nulabilidade: docs/schema.json, gerado por scripts/generate_cycle_contract.py.
Motor: monday_sla_orcamento/live_cycles.py; projecao/validacao: cycle_contract.py.
Valores nao finitos/negativos, datas invalidas, duplicidades e chaves orfas bloqueiam.
Consumidores: Power BI, analise de primeira entrega, revisoes e trabalho em andamento.

Antes de publicar: ensaio na populacao real, enriquecimento de cadastro para uso
final, validacao de totais por categoria, esquema de passagens com ciclo_id,
migracao do journal de tres para quatro destinos, testes de falha/recuperacao,
atualizacao diaria e reconciliacao real. Preservar v17 ate esses portoes passarem.
