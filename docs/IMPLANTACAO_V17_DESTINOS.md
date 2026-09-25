# V17 — SLA, fila e baixa qualidade

Estado: implantada e publicacao verificada pelo operador. Execucao daily
pipeline-monday-dtm7d, 1.363 projetos SLA / 4 fila / 816 baixa qualidade;
2.183 distintos sem duplicidade. Agenda retomada as 06h America/Sao_Paulo.
Ver recibo vigente em ESTADO_GCP_2026_09_24.md. Proxima rodada automatica pendente.
Os passos abaixo sao registro da implantacao; nao repetir inicializacao.

- ZIP: runtime/pipeline-monday-release-20260924-v17-destinos.zip
- SHA256: faa3142cf095e0c4455709f9c83039569c89263aa5657cfe6a757af44560f544
- 103 fontes/configurações e inventário conferidos contra workspace; sem .env/dados.
- Suíte completa: 578 aprovados, 3 pulados. Ruff nos arquivos alterados aprovado.
- Dois contratos físicos novos gerados: tabelas/monday_fila_precificacao e
  tabelas/monday_sla_baixa_qualidade_de_dado. SLA preserva schema v9.

## Ordem operacional

1. Upload do ZIP, conferir checksum, extrair em diretório novo. Build assíncrono
   tag v17-20260924; aguardar SUCCESS e registrar digest.
2. Manter pipeline-monday-diario pausado; conferir ausência de execução em curso.
3. Atualizar somente pipeline-monday, us-central1, imagem por digest validado,
   comando pipeline-monday, args initialize-destinations,--manifest,/app/pipelines.json,--writers-stopped.
4. Executar com --wait. Conferir evento destinations_initialized/status initialized.
   Esse passo cria as duas tabelas vazias e o journal, NÃO publica ainda os dados.
5. Alterar args para daily,--manifest,/app/pipelines.json e executar uma vez.
6. Conferir orchestration_end da execução exata; publication_verified=true para
   a consolidada e destinos no recibo. Executar sql/auditoria_destinos.sql.
7. Conferir destinations-control.json: pending=null, active com três descritores.
   Ler destinations/<geração>/report.json correspondente: balanced=true e totais.
8. Só após homologação retomar agenda. Programar refresh Power BI depois do
   término verificado; consultas independentes durante a troca podem ler gerações
   diferentes, mesmo com commit atômico no banco.

Não executar migrate_talent_contract.py ou outras migrações anteriores. Não mudar
IAM abrangente se houver Forbidden: identificar permissão/destino exato. A nova
publicação precisa de criação das duas tabelas na inicialização, DML nas três
tabelas e jobs BQ, além da leitura dos objetos no prefixo já autorizado. Não tocar LIA.

## Recuperação

O mesmo lock consolidado/diario protege ambos os modos. Depois de inicializado,
daily usa o journal destinations-control.json. Inicialização interrompida deve
ser repetida na mesma imagem; daily não prossegue enquanto initializing=true.
Timeout/resultados incertos preservam pending; execução seguinte consulta o mesmo
job ID e reconcilia. Não apagar locks/controles ou recriar tabelas para destravar.
Falha terminal do query job desfaz os DML da transação. Artefatos ficam preservados.
Não voltar para v16 sem plano de recuperação: o controle antigo foi preservado,
mas não acompanha a nova população filtrada.

## Aceite e limites

Referência do ensaio (não constantes para sempre): 1.363 projetos/6.366 passagens
SLA, 4 projetos fila, 816 projetos qualidade contendo evidências de 3.224 passagens.
Nenhum projeto em dois destinos; projetos totais 2.183; passagens representadas 9.594.
Tabelas dinâmicas exigem comparar com o report da MESMA publicação.
Espera da fila é observada até captura do cadastro, não esforço da equipe.
Cada rodada reconstrói candidatos das fontes, sem usar somente o SLA filtrado anterior.
Isso permite projetos saírem e voltarem de destino após correção.

Mantém recorte de mapa/título/Input/talento anterior. Não resolve 275 itens sem mapa
nem homologa continuidade dos 213 projetos entre contas. Alerta externo permanece
pendente. Implementação/testes locais não equivalem a publicação homologada.
