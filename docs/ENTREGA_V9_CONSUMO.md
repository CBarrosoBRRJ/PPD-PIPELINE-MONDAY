# V9 consumo direto — local, não implantado

Pacote runtime/pipeline-monday-release-20260923-v9-consumo.zip, 78 arquivos.
SHA256 7cf12064079f50d245e9485b709a734f02334b09a6032917569382c44963fd3a.
414 testes aprovados, 3 ignorados; Ruff aprovado, manifesto do ZIP conferido.

Contrato sla-consolidado-consumo-v4. Campos novos: sla_etapa_horas_uteis,
classificacao_consumo, motivos_inelegibilidade_kpi_json, versao_regra_kpi.
Todos calculados e validados em cada daily. Schema físico aditivo; não há tabela extra.
Não remove dados históricos. Não altera definição do KPI v3 nem libera total entre contas.

## Reconciliação local

Base v3 reconstruída a partir do artefato publicado v7 e política conferida:
89d4c1281e616533c16ba960bf1dfeee0f81432bb2fcf441e1a6b010303a1135.
Plano remoto deve confirmar esse hash antes de migração. Se diferente, parar.
V4 candidata: 3c3ee3cb5a92a96052687300f45efd287ff440f0620d169db4fd64aa961e8f78.
9.648 linhas preservadas; 6.227 métricas não nulas, 1.926 encerramentos observados,
509 sem saída observada, 986 evidência insuficiente. Categorias mutuamente exclusivas.
Nos campos anteriores só versao_contrato muda. Flags/durações/IDs/datas inalterados.
Reprodução: scripts/validate_consumption_upgrade.py; resultado privado em runtime.

## Implantação controlada

1. Conferir ZIP, build, teste offline de plan e contrato v4, push e registrar digest.
2. migrate_consumption_contract.py plan confirma identidade v3, hash base e geração.
3. Pausar apenas pipeline-monday-diario; job na imagem nova por digest em modo plan;
   apply --expected-generation <plano> --expected-image <digest>. Mesmo conjunto
   de proteções v8: nenhum escritor ativo, base esperada e CAS. Não muda tabela.
4. Executar daily na imagem nova. Publisher confere active v3 com schema antigo,
   escreve candidato v4 atomicamente e reconcilia schema/conteúdo antes de promover.
5. Conferir publication_verified e BQ: 9.648 linhas, 6.227 métricas não nulas;
   métrica igual a duracao_horas_uteis apenas nas elegíveis e NULL nas outras.
   Conferir classificação/motivos e fingerprint; retomar agenda somente após sucesso.

Não executar ALTER TABLE manual: o load substitui schema e dados numa publicação.
Referência: https://docs.cloud.google.com/bigquery/docs/managing-table-schemas
WRITE_TRUNCATE do pipeline existente é preservado. Não migrar com pending ou
execuções ativas. Falha mantém agenda pausada; não apagar journal/locks.
Não executar v8 após identidade v4. V2/v3 são leitura compatível, nunca candidato novo.
Sem mudanças em IAM, LIA, Terraform ou GitHub. Não repetir migração antiga incluída
como biblioteca no pacote: chamar somente migrate_consumption_contract.py.

## Consumo após recibo

AVG(sla_etapa_horas_uteis) por ambiente/status. COUNT desse campo é o denominador
do KPI; COUNT(*) inclui passagens fora do KPI. Contagem de projetos requer condição
campo não nulo. Não aplicar filtro de versão v3 depois da migração v4.
Usar tabelas/monday_sla_orcamento/sql/kpi_consumo.sql.
