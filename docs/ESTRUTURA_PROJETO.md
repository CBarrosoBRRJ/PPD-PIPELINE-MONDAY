# Organização por tabela

Uma pasta por entrega, sem multiplicar tabelas técnicas no BigQuery.

| Pasta | Construção/regras | Contrato e testes |
|---|---|---|
| monday_log_viu2 | src/monday_log_viu2/archive.py e structured.py | tests/test_archive.py, test_structured.py; README |
| monday_sla_orcamento_viu2 | src/historico_viu2: observations, passages, enrichment, review_contract | docs/CONTRATO_REVISAO_HISTORICA.md; tests/ |
| monday_sla_orcamento_globocorp | src/sls_orcamento_ppd: clients, rules, services, models, db | PRD.md, docs/CONTRATO_SLA_ORCAMENTO.md; tests/ |
| monday_sla_orcamento | src/monday_sla_orcamento/consolidation.py e publication.py | docs/CONTRATO_CONSOLIDADO.md, sql/, tests/ |

`orquestracao/` apenas coordena execução e verificação das dependências. A
publicação da consolidação saiu do coordenador e pertence agora à pasta da tabela.
Scripts de primeira carga usam módulos instalados ou helpers do ZIP autônomo;
os ZIPs já emitidos em runtime não foram alterados.

## Reutilização sem duplicar regras

O pacote sls_orcamento_ppd mantém utilitários de calendário, validação, GCS e
configuração usados pelos outros produtos. O pacote monday_log_viu2 disponibiliza
leitura/verificação de arquivo para historico_viu2. Imports e dependências são
explícitos nos pyproject.toml; não copiar uma regra para cada tabela.
Não mover todas as bibliotecas técnicas para outro pacote junto desta alteração:
isso aumentaria o risco sem modificar a responsabilidade dos produtos.
`compartilhado/` contém o pacote monday_comum, com a implementação única dos
filtros de título e Tipo de Input. Não é uma nova fonte de dados.

## O que esta mudança não faz

- Não muda regras de SLA, IDs, nomes de objetos GCS, estado, destino BQ ou agenda.
- Não cria tabelas de excluídos, brutos, staging ou backups.
- Não exclui monday_log_viu2 existente; sua permanência será alinhada com a
  orientação posterior de BQ somente para consumo tratado.
- Não apaga .env, runtime, arquivos privados ou estado necessário à atualização.
- Os filtros recebidos estão implementados em escopo-sla-v3; aplicação remota
  exige nova imagem e atualização histórica controlada, não apenas mover pastas.
- Não toca na LIA nem implanta esta árvore automaticamente.

## Antes de outra tabela

Definir origem, grão, chave, campos, regras e comportamento de falha; criar pacote,
contrato, testes e README na pasta correspondente. Adicionar ao manifesto somente
após implementar o adaptador e validar dependências. Atualizar Docker e allowlist
de release. Executar a suite da raiz e um replay local quando houver mudança de SLA.

## Estado da entrega

As quatro tabelas existem. A consolidada tem primeira carga conferida, não
homologada para KPI/ML. A integração diária continua candidata local. A release v4
anterior deve ficar sem implantação enquanto se concluem as regras de exclusão;
nova release será gerada depois dos testes dessa alteração de negócio.
