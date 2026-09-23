# Recuperação preventiva de rótulos históricos

## Pré-conferência remota (pacote preparado, execução pendente)

Pacote privado runtime/viu2-rotulos-preflight-20260923-v1.zip, SHA256
93cdcbca4c4c59e23768a54979c136748ab9ea0719160a2ca01272f490899e9c.
Contém somente base/candidata tratadas, schema, manifesto e script de leitura.
Não inclui .env, credenciais ou estado bruto. Não possui modo apply.
No Cloud Shell, plan_label_migration.py compara conteúdo integral da tabela
histórica com a base auditada e confere estabilidade por etag; lê identidade do
controle consolidado e recusa pending. Retorna lastModifiedTime para planejamento.
Não pausa agendas, não troca imagem e não altera tabela/controle/IAM.

Motivo: HISTORY_SHA e IDENTITY da consolidada fixam o histórico antigo; mudar
somente a tabela não atualiza a fonte da rotina diária. Migração coordenada e
permissão de leitura do novo objeto ainda precisam ser preparadas após conferência.
Não executar pacotes antigos de escopo ou reaplicar migrações concluídas.

## Auditoria Globocorp concluída na geração publicada

Estado 9c81b3ea7dba4d9b92798efc07cb479e recebido e checksum verificado.
Exportação normalizada pelo schema (incluindo FLOAT e timestamps) reproduz
exatamente gold_hash 5fbc58342d11717b48f035ec350ff4846535eeb40f00ca58ac88e904c6652814.
3.598 linhas / 2.466 projetos; cadastro vinculado por item/quadro/snapshot_at igual
ao cadastro_referencia_utc publicado. Zero cadastro ausente, Input não verificável,
Input proibido ou título proibido; 60 projetos com vazio comprovado permitido.
Auditoria reproduzível: produto Globocorp scripts/audit_published_input.py;
recibo privado runtime/validation/globocorp_input_audit_20260923.json.
Esta evidência substitui a pendência de Input Globocorp abaixo, somente para a
geração conferida. Não aprova automaticamente cronologia/identidade/KPIs nem
garante futuras cargas. Não altera GCP nem implanta o auditor no job diário.

## Auditoria de Input e pendências remanescentes

Auditoria local da candidata histórica contra contexto com checksums fixados:
14.761 passagens, 3.654 projetos; zero sem contexto e zero Input proibido;
67 projetos com Input vazio comprovado permitido. Verificação passou também
pela reaplicação do filtro integral. Implementada em audit_label_rebuild.py;
relatório privado reconciliation_with_input.json. Não comprova Input Globocorp:
a exportação BQ não contém o cadastro da geração ativa.

Na consolidada candidata: 32 desconhecidos = 16 código 5 sem rótulo, dez código
8 sem rótulo na entrada comprovada e seis código 4 bloqueados por eventos de
schema durante a passagem. Não remover essas barreiras por aprovação genérica.

## Revisão dos dois ciclos derivados

Conferência local da candidata: item ViU2 12322990458 passa a ter 705,748 horas
corridas (Entrada recuperada em 19/06 17:16:05.566Z até Encerrado em 19/07
03:00:57.398089Z). Item 11592459517 passa a ter 1.093,122 horas corridas (Entrada
25/03 13:53:07.837706Z até Encerrado 10/05 03:00:28.141723Z), após recuperar o
status intermediário Em Elaboração. Todos os limites adjacentes coincidem dentro
da mesma origem. Nenhuma data/duração de passagem foi modificada. Totais estavam
nulos e se tornaram calculáveis; não são horas úteis nem SLA completo entre contas.
Há pendências de schema/negócio; cálculo consistente não equivale à homologação.
Testes preventivos adicionais verificam recuperação, lacuna, troca de origem,
sobreposição e rótulo desconhecido. GCP permanece sem alterações.

## Conferência com exportação atual (23/09, 18:56Z)

Exportação Globocorp recebida em Downloads, SHA256 conferido:
e2e7f226acf9e4a448267e1b2915c8a736d821785c99d0b46efdb7dd977daff8.
3.598 linhas / 2.466 itens. Reconstrução com mapa fixado e contexto histórico:
9.648 linhas / 2.209 projetos antes e depois, corte 2026-09-23T03:00:00Z,
mesmo conjunto de interval_id. Desconhecidos: 37 para 32.
Mudanças na consolidada: cinco status_nome/pendencias/status_terminal/situacao,
11 registros de origem serializados e dois tempo_ciclo_observado_horas. Esses
dois totais derivados precisam de revisão específica antes de publicação; não
confundir preservação das durações das passagens com igualdade de todos os KPIs.
Demais campos iguais na comparação local. Não é fingerprint da consolidada
remota: é reconstrução a partir das origens. Nada publicado no GCP/GitHub.

Estado: implementação local candidata, não implantada. GCP permanece v6.
Regra `historical-labels-v2`, no enriquecimento do produto histórico viu2.

Origem: envelopes históricos e IDs de suporte/saída da passagem. Grão: passagem
por conta/quadro/item/status. Não altera chave, datas, durações ou schema BQ.
`qualidade_rotulo` identifica recuperação pelo previous_value do fechamento;
`eventos_saida_json` conserva a linhagem pública. Versão/evidência adicional no
artefato privado. Não cria tabela técnica nem concede aprovação de negócio.

Rótulo inicial comprovado prevalece. Na ausência dele, a recuperação exige saída
conhecida, evento listado na linhagem da saída, mesma conta/item/coluna/quadro
(quando informado), mesmo código anterior e timestamp efetivo exatamente igual.
Rótulos conflitantes ou eventos de schema durante a passagem impedem o fallback.
Sem evidência, permanece desconhecido; linhagem estrangeira bloqueia o lote.
Não há tolerância temporal arbitrária, dicionário fixo por código nem preenchimento
pelo cadastro atual. Os dez casos com horário divergente ainda exigem investigação.

## Publicação e paridade de versões

Não corrigir via UPDATE avulso no BQ. Reconstruir o histórico com estas regras,
comparar conteúdo/IDs/datas/durações e exclusões, publicar por procedimento
versionado e reconciliado; atualizar a fonte histórica fixada do coordenador e
reconstruir a consolidada. Uma nova imagem diária sozinha não refaz o histórico.

Antes de declarar local = GitHub = GCP: revisar diff e segredos, testar, registrar
commit do código aprovado, gerar release a partir desse commit, registrar SHA256
do pacote e digest da imagem, implantar por digest e confirmar publicação real.
Não executar commit/push/deploy implicitamente. .env, tokens, dados e tfstate não
integram o Git. Igualdade é do código/contratos versionados, não de credenciais
ou arquivos privados de cada ambiente. Enquanto houver alterações locais não
implantadas, registrar explicitamente a divergência.

Pendentes: ensaio integral sobre arquivo histórico, diferenças temporais do código
8, código 5 sem rótulo, auditoria de Input, continuidade entre contas e release.
Testes sintéticos não substituem esses controles ou homologação de indicadores.

## Ensaio local realizado em 23/09

Arquivo original verificado por `load_evidence`; reconstrução de 17.486 passagens:
88 rótulos recuperados antes do escopo. Após projeção/filtros: 14.761 passagens,
54 recuperações (código 0: 33; 4: 12; 7: 1; 8: 8), 126 ainda sem rótulo.
Reconciliação por chave confirmou conjunto de registros, IDs, datas, durações e
demais campos protegidos idênticos; somente status_nome, qualidade_rotulo e
pendencias_json mudaram. Script reproduzível: scripts/audit_label_rebuild.py.
Artefato candidato privado: runtime/validation/viu2_review_labels_v2/review.ndjson.gz,
SHA256 0a8016b8dd633fb1e94bc5b7f27c38f3b485174b3f1f76eaa8fa4481c6cf5cea.

Ensaio consolidado com captura Globocorp ANTIGA (não é a publicação GCP atual):
9.638 linhas antes/depois, 37 para 32 sem classificação. Apenas cinco das onze
passagens com rótulo na saída passaram pelas demais proteções; não prometer onze
correções só com base na consulta temporal. Conferência contra Globocorp atual
de 3.598 linhas ainda requer exportação correspondente, não a antiga de 4.237.

Amostra item 11415551656/código 8: entrada foi o changed_at do evento em lote
(18:34:28.280000Z); evento individual com Encerrado tem created_at nativo
18:34:40.216913Z e action UUID nulo. São relógios/evidências diferentes; não prova
erro humano nem defeito Monday. Não arredondar nem deslocar a entrada. A semântica
do rótulo posterior continua pendente de política/evidência, sem preencher por
proximidade. Amostra código 5 tem evento individual com rótulo ausente; sem nome
comprovado, continua desconhecido. Nada foi publicado ou alterado no GCP.
