# V8 KPI por etapa — local, implantação pendente

Release: runtime/pipeline-monday-release-20260923-v8-kpi-etapa.zip (76 arquivos).
SHA256: 49c2a13931fc038a4a6ab5ac842f1d7580ec485de7e622d31f3c26477e7239ca.
Inclui migrate_kpi_contract.py na raiz, além de release-manifest.json com hashes
dos arquivos. Nenhum dump, .env, estado ou credencial no pacote de código.
Validação final local: 402 passed, 3 skipped; manifesto dos 76 arquivos conferido.
Casos de migração cobrem geração/base divergentes, pending, agenda ativa,
idempotência e preservação do descriptor ativo. Nenhum deploy GCP executado localmente.

Contrato sla-consolidado-etapa-v3, política kpi-etapa-origem-v1. Nenhuma tabela
nova nem mudança no schema físico. Cada daily recalcula aprovação local por
passagem; não libera continuidade entre ambientes. Schema/DDL/dicionário gerados.

Base publicada v7 reconciliada: 9.648 linhas, fingerprint
6c33244f4fff85a9f5ebd0e09685aed8a6bf746eb0f5d8df92e7b91363447987.
Candidata v3 sobre mesma base: 6.227 elegíveis (6.202 ViU2/25 Globocorp),
fingerprint 89d4c1281e616533c16ba960bf1dfeee0f81432bb2fcf441e1a6b010303a1135.
Somente versao_contrato/validacao_negocio/elegivel_comparacao alterados.

## Operação

1. Upload do release, checksum, build, teste offline e push por digest.
2. Executar migrate_kpi_contract.py plan (incluído na raiz do ZIP); sem escrita.
3. Pausar somente pipeline-monday-diario; nova imagem em comando pipeline-monday,
   args plan,--manifest,/app/pipelines.json. Não executar daily prematuramente.
4. Executar migrate_kpi_contract.py apply --expected-generation <plano>
   --expected-image <imagem-por-digest>. Verifica agenda, imagem, modo plan,
   execuções concluídas, identidade e fingerprint de base; CAS só muda contrato
   do controle. Mantém descriptor active v2 até nova publicação. Nenhuma carga BQ.
5. Restaurar daily, executar e verificar publicação v3, números, fingerprint e KPI.
   Só então retomar agenda. Em falha, manter pausa, não apagar controle/lock.

Se base mudou por execução diária, script recusa plano/apply: auditar nova base,
não trocar constante nem forçar geração. Imagem antiga não aceita identidade v3.
Não executar outro escritor durante janela de migração. LIA e IAM intocados.
Código aceita validação v2 para conferir active antigo, mas recusa novo publish v2.

## Consumo após conferência

Usar sql/kpi_etapa.sql, explicitar população selecionada, ambiente/status e
denominador de passagens. Não classificar no prazo/atrasado sem meta contratada.
Não somar totais entre contas. Demais passagens ficam na tabela, fora do KPI;
aberta sem saída não prova abandono e terminal não acumula duração após fechamento.
Documentação: HOMOLOGACAO_KPI_ETAPA.md. GitHub sem push, Terraform sem apply/destroy.
