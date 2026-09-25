# PPD-PIPELINE-MONDAY

Pipelines do Monday organizados por tabela de consumo no BigQuery.

O nível compartilhado é **pipeline-monday**, sem referência a orçamento. Orçamento
é um produto, não a plataforma inteira. Consulte a
[separação entre plataforma e produtos](docs/PADRAO_NOMES_TABELAS.md).
O estado publicado mais recente é o **v18 de ciclos** (25/09/2026), com
`monday_sla_orcamento` por passagem, `monday_ciclos_orcamento` por tentativa,
fila de Entrada e diagnóstico de qualidade por projeto. Consulte o
[recibo e procedimento v18](docs/ENTREGA_V18_CICLOS.md) antes de operar o job.
O agendamento diário foi reativado; a primeira execução automática após essa
liberação ainda precisa de conferência. A documentação v12/v17 permanece como
histórico, não como contrato vigente. Não repetir migrações nem implantar
releases anteriores.
Veja a [organização das iniciativas no GCP compartilhado](docs/ORGANIZACAO_INICIATIVAS_GCP.md).

## Organização

```text
tabelas/
  monday_log_viu2/                # Código do resgate/log já existente
  monday_sla_orcamento_viu2/      # Reconstrução e contrato do SLA histórico
  monday_sla_orcamento_globocorp/ # Coleta, regras e publicação da origem atual
  monday_sla_orcamento/           # Identidade, consolidação e publicação unificada
orquestracao/                     # Ordem, dependências e adaptadores de execução
compartilhado/                    # Política de reutilização e futuras regras comuns
infra/            # Infraestrutura GCP gerenciada em conjunto
docs/             # Ambiente e organização do repositório
.github/          # CI e deploy por produto
.vscode/          # Configuração do editor
```

Cada pasta tem código em `src/`, testes em `tests/`, ferramentas em `scripts/`
e um README com origem, grão, contrato e limitações. Os nomes dos pacotes Python
legados são preservados quando necessário; nomes de pasta não alteram IDs GCP.
Consulte o [mapa de responsabilidades](docs/ESTRUTURA_PROJETO.md).
Direção analítica: [continuidade por projeto entre viu2 e globocorp](docs/CONTINUIDADE_PROJETOS_MONDAY.md).
Consolidação depende de correspondências verificadas, sem descarte por data de criação.
[Guia da equipe para KPIs e ML](docs/GUIA_DADOS_EQUIPE.md): situação atual, qualidade,
limites temporais e critérios de homologação antes de usar os dados em produção.
As coleções Bronze/Silver e pendências são internas desse produto; não são novas tabelas públicas.

## Desenvolvimento na raiz

```powershell
python -m pip install -e ./compartilhado -e "./tabelas/monday_sla_orcamento_globocorp[dev]"
python -m pip install --no-deps -e ./tabelas/monday_log_viu2 -e ./tabelas/monday_sla_orcamento_viu2 -e ./tabelas/monday_sla_orcamento -e ./orquestracao
python -m pytest -q
python -m ruff check tabelas orquestracao compartilhado
python tabelas/monday_sla_orcamento_globocorp/scripts/generate_ddl.py
python tabelas/monday_sla_orcamento_globocorp/scripts/generate_contract_docs.py
python -m pipeline_monday.cli plan --manifest orquestracao/deploy/pipelines.json
```

A .venv e os arquivos privados existentes (.env, runtime e backups) permanecem em seus locais.
O comando `sla-pipeline` continua disponível após reinstalar o pacote.
Execute-o na raiz para manter os caminhos relativos atuais; selecione configurações
explicitamente com `sla-pipeline --env-file .env.gcp COMANDO`.
Não execute coleta/publicação apenas para validar esta reorganização.

## Dashboard e melhoria do processo

Para consultar as tabelas atuais, use o
[guia SQL de gestão, indicadores e ML v18](docs/CONSULTAS_GESTAO_SLA_E_ML_V18.md).
Cada visão inclui interpretação e ação; o guia define os contratos dos KPIs,
metas propostas e marcos de homologação. O
[plano de execução de ML](docs/PLANO_EXECUCAO_ML_V18.md) detalha preparação de
dados, modelos, avaliação temporal e pilotos para prazo, demanda e capacidade.
Leia também o [plano gerencial histórico de KPIs e ML](docs/PLANO_DASHBOARD_ML.md), abra o
[protótipo HTML ilustrativo](powerbi/sla_gestao/prototipo.html) no navegador e siga
o [guia Power BI](powerbi/sla_gestao/IMPLEMENTACAO.md). São propostas de consumo,
não um dashboard publicado nem homologação do SLA global ponta a ponta.

## Expansão de produtos

Cada nova tabela terá sua pasta `tabelas/<nome_da_tabela>/`, com código, testes,
contrato, documentação e deploy próprios. Antes de implementar, definir origem,
grão, chaves, tipos, nulos, regras, consumidores e recuperação em falha.
Separar tabela de destino, prefixo GCS e identidade de execução.

Componentes só serão extraídos para uma biblioteca compartilhada quando houver
reutilização comprovada. Por enquanto, os clientes Monday e BigQuery continuam
junto de sla_orcamento: ainda dependem dos contratos desse produto.
A infraestrutura da raiz atende hoje sla_orcamento e exige revisão ao adicionar produtos.

Veja [ambiente](docs/AMBIENTE_DESENVOLVIMENTO.md),
[regras do produto](tabelas/monday_sla_orcamento_globocorp/PRD.md) e
[operação](tabelas/monday_sla_orcamento_globocorp/OPERATIONS.md).
