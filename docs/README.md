# Documentação — índice

A versão vigente é a **v19** (modelo de consumo, com uma tabela por pergunta). Comece pelos documentos "Vigentes".
Os "Históricos" registram decisões e implantações anteriores. Servem de contexto e **não** são procedimento atual.

## Vigentes

| Documento | Para quê |
| :--- | :--- |
| [IMPLANTACAO_V19.md](IMPLANTACAO_V19.md) | Passo a passo de produção: v19 no ar e v18 apagada com backup |
| [IMPLANTACAO_V18_1_ESTABILIDADE.md](IMPLANTACAO_V18_1_ESTABILIDADE.md) | Correções de estabilidade; comandos de segurança (IAM) e do alerta "25 h sem sucesso" |
| [ESCALA_E_CUSTO.md](ESCALA_E_CUSTO.md) | Como os pipelines crescem sem quebrar e sem custo alto; checklist para pipelines novos |
| [../tabelas/monday_sla_orcamento/docs/CONTRATO_MODELO_V19.md](../tabelas/monday_sla_orcamento/docs/CONTRATO_MODELO_V19.md) | Contrato das 17 tabelas v19 (gerado pelo código) |
| [REVISAO_TECNICA_V19_2026_09_28.md](REVISAO_TECNICA_V19_2026_09_28.md) | Revisão técnica da v19 e correções da regra `modelo-v19-2` |
| [REGRAS_ESCOPO_SLA.md](REGRAS_ESCOPO_SLA.md) | Escopo: títulos, PACOTE, Tipo de Input |
| [CONTINUIDADE_PROJETOS_MONDAY.md](CONTINUIDADE_PROJETOS_MONDAY.md) | Como as contas ViU2 e Globocorp são unidas num mesmo projeto |
| [PADRAO_NOMES_TABELAS.md](PADRAO_NOMES_TABELAS.md) | Padrão de nomes `monday_*` |
| [ORGANIZACAO_INICIATIVAS_GCP.md](ORGANIZACAO_INICIATIVAS_GCP.md) | Projeto GCP compartilhado; isolamento da LIA |
| [INVENTARIO_BUCKETS.md](INVENTARIO_BUCKETS.md) | Buckets e prefixos |
| [ALERTAS_MONITORING.md](ALERTAS_MONITORING.md) | Alertas do Cloud Monitoring |
| [AMBIENTE_DESENVOLVIMENTO.md](AMBIENTE_DESENVOLVIMENTO.md) | Ambiente local |
| [ESTRUTURA_PROJETO.md](ESTRUTURA_PROJETO.md) | Mapa das pastas e responsabilidades |
| [GUIA_DADOS_EQUIPE.md](GUIA_DADOS_EQUIPE.md) · [PROJETO_EXPLICADO.md](PROJETO_EXPLICADO.md) | Explicação do projeto para a equipe |

**Regras de negócio, decisões e propostas ao time:** ficam na nota do projeto no Obsidian
(`SecondBrain/Trabalho/Rede Globo/Projetos/ppd-pipeline-monday.md`), que é a fonte de verdade das regras R1–R20.

## Históricos (antes da v19)

| Tema | Documentos |
| :--- | :--- |
| Entregas v5–v18 | ENTREGA_V5_ESCOPO · ENTREGA_V7_ROTULOS · ENTREGA_V8_KPI_ETAPA · ENTREGA_V9_CONSUMO · ENTREGA_V10_TRAJETORIA · ENTREGA_V11_ESTIMATIVAS · ENTREGA_V12_DURACAO_UNIFICADA · ENTREGA_V18_CICLOS · ENTREGA_CONSUMO_ATUAL · FECHAMENTO_ENTREGA_MONDAY |
| Implantações v13–v17 | IMPLANTACAO_V13_CANDIDATA · IMPLANTACAO_V14_TALENTOS · IMPLANTACAO_V15_ESCOPO_TALENTOS · IMPLANTACAO_V16_VALIDACOES · IMPLANTACAO_V17_DESTINOS |
| Recibos de estado do GCP | ESTADO_GCP_2026_09_21 · ESTADO_GCP_2026_09_22 · ESTADO_GCP_2026_09_23 · ESTADO_GCP_2026_09_24 · RETOMADA_2026_09_25 |
| Migrações e correções | MIGRACAO_NOME_SLA · RENOMEACAO_PROJETO · CARGA_SLA_VIU2_NOME_FINAL · CORRECAO_V6_CONTEXTO · RECUPERACAO_ROTULOS_HISTORICOS · UPGRADE_PRECIFICACAO_EM_ANDAMENTO |
| Análises da v18 | CONSULTAS_GESTAO_SLA_E_ML_V18 · VALIDACAO_E_ANALISE_CICLOS_V18 · PLANO_EXECUCAO_ML_V18 · PLANO_DASHBOARD_ML · QUERIES_ANALISE_VALIDACAO_SLA · ENSAIO_CICLOS_CONTINUOS · GUIA_TABELAS_E_CICLOS_CONTINUOS |
| Regras e auditorias anteriores | REGRA_ENTRADA_PROJETO · SEPARACAO_SLA_FILA_QUALIDADE · HOMOLOGACAO_KPI_ETAPA · VALIDACOES_CONTINUAS_SLA · COMPATIBILIDADE_SLA_ORIGENS · LEGENDA_CADASTRO_SLA · RECORTE_PRECIFICACAO_ATUAL · AUDITORIA_VINCULOS_20260924 · CANDIDATOS_IDENTIDADE_2026_09_22 · ATUALIZACAO_DIARIA_CONSOLIDADO · CONTINUAR_NO_VSCODE |

> As consultas SQL da v18 apontam para tabelas apagadas em 28/09/2026 (backup Avro em `backups/v18_20260928`).
> Para análises novas, use as tabelas `monday_sla_*` do contrato v19.
