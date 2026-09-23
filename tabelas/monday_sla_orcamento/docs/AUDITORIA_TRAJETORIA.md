# Auditoria preventiva da trajetória

Implementação local: trajectory.py, política auditoria-trajetoria-v1.
Não implantada. Evolução v5 acrescenta qualidade por projeto ao schema; mantém
IDs, datas e elegibilidade por etapa da v4. Implantação candidata: release v10.

Grão do diagnóstico: um projeto_id, reunindo os IDs nativos das duas origens.
A auditoria roda na construção e na validação antes de publicação. Rejeita ordem
duplicada/descontínua, ordem incompatível com datas, pares de IDs inconsistentes,
item incompatível com origem e saída anterior à entrada. Erros não expõem dados.
O relatório operacional traz somente contagens agregadas, sem tabela adicional.

Lacunas são limitações de evidência, não motivo para apagar etapas válidas:
passagem única, início diferente de Entrada, status desconhecido, transições sem
continuidade temporal, sobreposição, fronteira entre contas e último registro
não terminal. A igualdade de datas não comprova a migração entre ambientes.
Sem limitações detectadas NÃO equivale a histórico completo aprovado: eventos
ausentes da fonte não podem ser descartados como possibilidade só por este teste.
O diagnóstico nunca aprova SLA total ou elegibilidade genérica para ML.

scripts/audit_trajectory.py lê snapshot NDJSON gzip e exige SHA256 esperado.
Não consulta APIs, não altera arquivos-fonte e não escreve no GCP.
sql/trajetoria_projeto.sql fornece a consulta parametrizada do histórico observado.
No Cloud Shell, SQL deve ser passado a bq query, não executado diretamente no Bash.

Para encerrar a homologação: confrontar lacunas com eventos-fonte, recuperar
somente transições comprovadas, definir contrato de qualidade por projeto e
testar/publicar evolução versionada. Não substituir NULL pela próxima entrada
entre contas. Não renumerar ou alterar manualmente linhas no BigQuery.

## Resultado offline em 23/09/2026

Snapshot publicado v7, SHA256
e892c698bf6f5656f47b9beee3e3a0fdb7bb72904de4105d43c1a035eb5f0e6f:
9.648 passagens e 2.209 projetos. Não é nova consulta ao BigQuery atual.

| Limitação | Projetos |
|---|---:|
| Passagem única | 53 |
| Somente registros terminais | 32 |
| Primeiro registro diferente de Entrada | 614 |
| Transição sem continuidade temporal | 193 |
| Fronteira entre ambientes não comprovada | 191 |
| Status sem classificação | 32 |
| Último registro não terminal | 326 |

Categorias se sobrepõem. 1.161 projetos não apresentaram essas limitações
estruturais; isso NÃO aprova histórico completo ou SLA total.

Cruzamento dos 53 projetos de passagem única com coordinator_source.ndjson.gz
histórico e exportação globocorp-000000000000.json.gz: cada projeto tem uma
passagem ViU2 com início e uma referência Globocorp sem início observado.
São 53 referências sem entrada comprovada, não 53 etapas datadas perdidas na
consolidação. Não preencher a data pela criação da cópia. Ainda é necessário
investigar eventos-fonte antes de concluir impossibilidade de recuperação.

Testes locais após inclusão da auditoria: 423 aprovados, 3 ignorados;
Ruff do produto aprovado. Nenhuma mudança em GCP ou publicação executada.

## Projeção para consumo v5

Os cinco campos do PRD tornam o diagnóstico visível na mesma tabela. Todos são
derivados do lote completo, nunca da página ou do item isolado da consulta do BI.
Os 1.048 projetos com limitações mantêm suas passagens válidas; 1.161 têm sequência
observada sem lacunas detectadas. Não conceder elegibilidade geral para SLA total/ML.
Script validate_trajectory_upgrade.py reconcilia a v4 fixada com a candidata v5.
Fingerprint v5: b676c79b17237437c193bb28fde297ad9452b6ab34250a5bf9670c30ee53a895.
Nenhum campo anterior muda, exceto a versão; 6.227 valores de KPI preservados.

O mesmo script consulta o estado local Globocorp com checksum
3889bde42e846f7ef3768df4e4d88d0cfe575d0997ac29306cdf13b77703bfe0:
zero eventos Bronze de status para os 53 itens Globocorp correspondentes aos
projetos de passagem única. Isso limita a recuperação nessa captura, não prova
ausência de eventos em todas as fontes externas ou em capturas posteriores.
