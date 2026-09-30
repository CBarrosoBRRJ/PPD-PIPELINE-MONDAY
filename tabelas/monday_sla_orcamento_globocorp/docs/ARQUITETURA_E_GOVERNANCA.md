# Governança de dados — GCP

Este documento é normativo junto de [PRD](../PRD.md), [arquitetura](ARQUITETURA_GCP.md), [dicionário](OURO_CONSUMO.md) e contratos executáveis `models/contracts.py` e `models/bq_consumption.py`.

## Evidência e identidade

- Origem: um quadro/coluna Monday por destino. IDs e UUIDv5/SKs existentes são preservados.
- Bronze guarda envelopes originais. Limpeza ocorre em cópias analíticas; nunca reescrever a fonte para aparentar consistência.
- Não inventar Entrada, datas, autoria histórica ou durações. Desconhecido é NULL; zero exige evidência.
- Normalização textual: Unicode NFC, espaços nas bordas/repetidos; manter acentos e caixa de apresentação. Não fundir entidades por semelhança de nome.
- Um projeto pode ter muitas passagens e retornos. Somar durações por passagem; métricas totais repetidas exigem MAX por projeto.
- Atributos refletem o cadastro observado na coleta; não comprovam os atributos de todos os momentos passados.

## Contratos e publicação

Toda mudança declara origem, grão, tipos, chaves, nulabilidade, tratamento, consumidores e ação em falha. Os 20 contratos internos são coleções GCS, não tabelas BQ. Este produto publica `monday_sla_orcamento_globocorp` (39 campos, chave interval_id; nome histórico: sla_orcamento, apagado em 22/09/2026). As tabelas de consumo vigentes são as do modelo `monday_sla_*`/`monday_dim_*`, publicadas pela consolidada; o contrato delas está em `tabelas/monday_sla_orcamento/docs/CONTRATO_MODELO_V19.md`.

Tipos, unicidade, escopo, relações, coerência temporal e elegibilidade são validados em Python. BigQuery não substitui PK/FK/CHECK do PostgreSQL; schema REQUIRED e carga atômica complementam as verificações. Rejeitar lote inconsistente e conservar a publicação anterior. Mensagens nunca incluem valores rejeitados.

A reserva diária antecede a extração; watermark só avança com publicação reconciliada. Checkpoint imutável, journal e job ID permitem recuperar falhas entre GCS e BQ. Lock não expira automaticamente, de propósito (impede dois escritores). Se o job for morto e a trava ficar, liberar com `inspect-lock` e `unlock --lock-generation N --execution-stopped` (procedimento em docs/ESTADO_GCP_2026_09_21.md); nunca apagar o objeto à mão.

## Qualidade, calendário e operação

Horas úteis: seg-sex, 10h–13h e 14h–19h, São Paulo, BR PUBLIC e extras configurados. A consolidada usa só BR PUBLIC e recusa rodar se `BUSINESS_HOLIDAYS` tiver valores (evita duas contas de horas diferentes); em produção a lista está vazia. Sem meta de SLA definida. Comparar somente passagens elegíveis. Calendário e regras versionados; mudança de regra requer testes e replay.

`quality-profile` grava relatório privado GCS; `validate` verifica derivados; `validate-gold` reconcilia publicação; `health` verifica sucesso e atualidade. Ausência de alertas não prova saúde: canais externos ainda precisam de implantação.

Segredos, checkpoint, dumps e dados brutos ficam fora do Git/logs. Runtime usa identidade própria com menor privilégio. Backup deve incluir ponteiros e todos os objetos referenciados; testar restauração isolada.

## Mudanças e expansão

Testar casos felizes e falhas. Executar os dois geradores após mudar contratos. Testes nunca usam dados fictícios na VPS ou dataset de produção. O importador PostgreSQL/SQLite é somente leitura e opcional; não existe mais escritor PostgreSQL.

Para outras origens, explicitar namespace de identidade e correspondências. Separar prefixos, tabelas e identidades; não presumir que IDs iguais de sistemas distintos são a mesma entidade. Medir volume, memória, duração e custo antes de ampliar: o pipeline ainda reconstrói histórico em memória.

Implantação, backup restaurado e primeira execução diária só podem ser declarados concluídos com evidência real.
