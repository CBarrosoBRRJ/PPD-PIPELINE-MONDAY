# Manutenção do PIPELINE-MONDAY

Estado operacional mais recente: docs/ESTADO_GCP_2026_09_23.md prevalece sobre
anotações cronológicas abaixo. V12/contrato v7 implantada; execução
pipeline-monday-jdc47 e durações unificadas conferidas no BQ pelo operador.
Agenda ativa confirmada. Próxima execução automática v12 pendente de observação;
ver docs/ENTREGA_V12_DURACAO_UNIFICADA.md. Durações unificadas têm proveniência;
não confundir análise com estimativas com o KPI estritamente observado.
Agenda/job/bucket legados excluídos pelo
operador; contas de serviço antigas continuam ativas. Não repetir migrações,
recriar recursos removidos nem aplicar/destruir Terraform legado. Não tocar LIA.

O projeto reúne produtos de dados do Monday. O produto implementado atualmente é `sla_orcamento`; novas tabelas dependem de contratos e publicação/recuperação definidos antes da implementação. A renomeação do repositório não altera IDs/SKs, estado nem recursos GCP do produto existente.

Cada produto fica em tabelas/<nome_da_tabela>/. O atual fica em tabelas/monday_sla_orcamento_globocorp/.
Leia PRD.md, docs/ARQUITETURA_E_GOVERNANCA.md, docs/ARQUITETURA_GCP.md e os contratos executáveis dentro dessa pasta antes de alterar regras, modelo ou publicação.
Os caminhos de código, scripts e documentação abaixo são relativos à pasta do produto.
Na raiz, instale com python -m pip install -e "./tabelas/monday_sla_orcamento_globocorp[dev]" e teste com python -m pytest -q.
Infraestrutura Terraform e configuração do editor permanecem na raiz. Não mover arquivos privados, estado ou .env junto com o código.

- Pipeline corrente: gglobo-viu-dados-hdg-prd.viu_agenciamento.sla_orcamento. Estado, Bronze, pendências e controle privados no GCS. Cloud Scheduler + Cloud Run Job daily.
- Decisão de 21/09/2026: historico_viu2 é uma carga única independente, sem agenda. Preservar log bruto privado no GCS; destinos históricos propostos log_monday_viu2 e sla_orcamento_viu2 exigem validação antes de publicação. Não sobrescrever a Gold corrente. Corte temporal e correspondência entre contas precisam de evidência; não inferir migração por nomes iguais ou criação da cópia.
- Refinamento de 21/09: análise deve preservar início ao fim do projeto entre contas; seguir docs/CONTINUIDADE_PROJETOS_MONDAY.md. Não descartar eventos/projetos por corte presumido. Histórico bruto já publicado conforme recibo; SLA histórico e consolidação ainda pendentes. Deduplicação da fronteira exige evidência, não UNION cego de durações.
- Nomes finais aprovados: sla_orcamento_viu2 congelada, sla_orcamento_globocorp diária da origem nova e sla_orcamento unificada oficial para KPIs. A tabela/deploy existentes ainda são legados, não consolidados. Migrar escritor/estado/agenda antes de reutilizar o destino final; não permitir dois escritores nem alterar BQ_TABLE isoladamente sobre estado existente.
- Isolamento obrigatório: lia-leitura-inteligente-scheduler e todos os recursos da LIA pertencem a outro projeto de negócio crítico e estão fora do escopo. Não alterar sua agenda, serviços, contas, permissões, dados ou buckets. Não copiar a LIA para o bucket deste pipeline. Toda operação GCP deve ter alvo exato do pipeline de orçamento; não fazer mudanças abrangentes no projeto compartilhado.
- Padronização posterior aprovada: nomes finais monday_log_viu2, monday_sla_orcamento_viu2, monday_sla_orcamento_globocorp e monday_sla_orcamento (unificada). Substitui os nomes planejados acima, não os recursos implantados automaticamente. Ver docs/PADRAO_NOMES_TABELAS.md. Agenda de orçamento foi pausada pelo usuário após falha de memória; recuperar e validar antes de retomar.
- O objetivo é estudar permanência por etapa; não há metas de prazo. Todos os joins e horas úteis em Python: seg-sex 10–13h / 14–19h, feriados BR PUBLIC automáticos e extras configuráveis.
- Nível geral/master usa pipeline-monday, sem orcamento. Nomes de produto mantêm o tema específico. Coordenador multiproduto ainda não existe; não tratar renomeação do job atual como implantação de orquestração. Não renomear recursos corporativos compartilhados ou da LIA. Ver docs/PADRAO_NOMES_TABELAS.md.
- Atualização: orquestracao/ contém coordenador inicial local, com processos sequenciais e apenas adaptador do SLA existente. Não implantado; não consolida contas ou escreve histórico viu2. O projeto GCP é da área e abriga N iniciativas; bucket dedicado não implica isolamento IAM auditado. Ver docs/ORGANIZACAO_INICIATIVAS_GCP.md.
- Preserve Bronze e IDs/SKs. Não preencher desconhecido com zero ou evento/data inventados. Total começa apenas na Entrada comprovada.
- Mudanças declaram origem, grão, tipos, chaves, nulabilidade, tratamento, consumidores e ação em falha.
- Modelo/contrato: execute scripts/generate_ddl.py e scripts/generate_contract_docs.py; atualize dicionário, PRD, KPIs e testes. Operação: atualize implantação/recuperação.
- PostgreSQL/SQLite são apenas origem de migração. migration/readers.py é somente leitura; não reintroduzir escritor PostgreSQL, cron/VPS ou tabelas técnicas BQ.
- Não apagar .env, volumes/checkpoint, backups ou tabelas reais. Remoções de dados precisam de escopo explícito, backup e reconciliação. Testes reais somente em ambientes locais/isolados opt-in.
- Segredos, dumps, dados brutos, credenciais e tfstate ficam fora do Git/logs. Nunca exibir valores rejeitados ou pedir chaves no chat.
- Diferenciar implementado/testado localmente de implantado/homologado. Alertas, GCP real e agendamento observado exigem evidência.
- Outras fontes exigem namespace e correspondências explícitas; IDs iguais não provam identidade entre sistemas.

## Estado posterior confirmado em 22/09/2026

Esta atualização prevalece sobre as anotações cronológicas de implantação acima.
Coordenador pipeline-monday implantado (imagem v3), manifesto com somente SLA;
agenda pipeline-monday-diario habilitada às 06h Brasília. Publicação diária pelo
coordenador ainda não comprovada; antiga pipeline-orcamento-diario pausada.
Estado ativo está no bucket dedicado ppd-pipeline-monday; identidade e BQ_TABLE
migrados para monday_sla_orcamento_globocorp, validate-gold concluído pelo operador.
Não executar o job antigo com identidade divergente. monday_log_viu2 e complemento
do resgate preservados no GCP com validação. SLA viu2 e consolidado NÃO publicados.
Artefatos locais de observações/passagens/enriquecimento são rascunhos privados,
não o contrato público: mantêm entradas conhecidas com durações desconhecidas e
lacunas intermediárias que o contrato corrente ainda não representa. Não publicar
esses JSONs diretamente nem relaxar validate_public para forçar compatibilidade.
Evidências e pendências atuais: docs/ESTADO_GCP_2026_09_22.md e
tabelas/monday_sla_orcamento_viu2/docs/RECONCILIACAO_LOTES_2026_09_22.md.

### Recibo posterior de publicação histórica

Operador confirmou carga de monday_sla_orcamento_viu2: 17.486 linhas, schema e
contagem verificados, sem expiração, job historical_sla_viu2_v1_e3cb6b12674bed2591df6ea9.
Contrato sla-viu2-review-v1 com validação de negócio pendente e KPI não aprovado.
Não é consolidado nem tem atualização diária. Esta confirmação substitui apenas
a pendência de carga histórica acima; monday_sla_orcamento continua não publicado.

### Recibo posterior da consolidação e decisão de limpeza

Operador confirmou conteúdo integral de monday_sla_orcamento: 11.252 linhas,
2.640 projetos, schema e fingerprint iguais ao pacote v3, tabela estável durante
a conferência. Esta evidência substitui a pendência de primeira publicação acima.
KPI não aprovado e atualização diária da consolidação ainda não integrada.
Usuário quer remover do BQ os legados sla_orcamento e
backup_sla_orcamento_pre_migracao_20260921 após preservação verificada no GCS
e inspeção de dependências. Não criar outro dataset BQ de backups para essa limpeza.
Não excluir jobs/buckets antigos antes dos respectivos controles de recuperação
e dependências. LIA e recursos compartilhados permanecem fora do escopo.

### Limpeza BQ confirmada e automação candidata

Operador excluiu as duas tabelas legadas após confirmar ausência de consumidores;
listagem contém apenas as quatro monday_*. Avro/metadados legados continuam GCS,
sem prova de restauração integral. Não repetir exclusões nem recriar legados.
Automação local da consolidação em orquestracao, com diário/lock próprios;
ver docs/ATUALIZACAO_DIARIA_CONSOLIDADO.md antes de publicar imagem nova.
Manifesto local agora tem dois produtos; isso não comprova implantação no GCP.

### Organização e filtros posteriores

Pastas reais: tabelas/monday_log_viu2, monday_sla_orcamento_viu2,
monday_sla_orcamento_globocorp e monday_sla_orcamento. Orquestracao apenas coordena;
consolidação/publicação pertencem à pasta da consolidada. Compartilhado é pacote
monday_comum com política escopo-sla-v3. Ler docs/REGRAS_ESCOPO_SLA.md.
Usuário definiu títulos excluídos e PACOTE somente no início; Tipo de Input exclui
apenas ViU First/Proativo. Vazio entra. Não criar tabelas extras de raw/excluídos/backup.
Decisão posterior explícita: excluir projetos históricos sem contexto de Input
verificável (300 na captura), propagando a exclusão ao par consolidado. Vazio
comprovado continua permitido. Não apagar os dados-fonte ao aplicar esse filtro.
Alterações locais ainda não publicadas. Não implantar ZIP v4 anterior aos filtros.
LIA intocada; nenhuma remoção GCS nesta organização. Workflow de deploy legado
desabilitado localmente para impedir recriação do escritor/destino removidos.
