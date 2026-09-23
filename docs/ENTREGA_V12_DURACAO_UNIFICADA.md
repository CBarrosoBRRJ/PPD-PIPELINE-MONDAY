# V12 — duração unificada para análise (implantada e conferida)

## Recibo do operador — 23/09/2026

Build e teste do contrato concluídos. Imagem publicada por digest
33263084d9f61172bf13b509c6df86ac195a3bff369c2d346c5d49d705dc6286.
Migração retornou contract_migrated, geração 1790203059154368 (da migração,
não da publicação posterior). Execução pipeline-monday-jdc47 concluída com sucesso.
Consulta BQ sem cache confirmou contrato v7: 6.227 observadas validadas,
191 estimadas e 3.230 indisponíveis; zero divergências em ambas as durações.
KPI observado preservado em 6.227 passagens. Scheduler retomado pelo operador:
ENABLED, 0 6 * * *, America/Sao_Paulo. Próxima execução automática ainda não
observada. Commit/push e correspondência com GitHub ainda não confirmados.

### Fechamento Git e correção de CI posterior

Commit d0f0f56 publicado na main; 84 arquivos locais conferidos contra o pacote
v12 antes do commit. Suíte final local: 465 aprovados / 3 ignorados.
CI 35930769915: infraestrutura aprovada; lint rejeitou três blocos de imports.
Reprodução confirmou interferência do antigo src/ local com caches na detecção
de imports do Ruff. Configuração src explícita na raiz e ordenação corrigida
nos três módulos da orquestração, sem mudança de regras ou destinos.
Esta correção posterior ainda não faz parte da imagem v12: código-fonte desses
três módulos difere na ordenação dos imports. Não declarar igualdade byte a byte
entre a imagem implantada e a main após esta correção. Nenhum redeploy GCP feito.

Pacote runtime/pipeline-monday-release-20260923-v12-duracao-unificada.zip,
84 arquivos de código, manifesto SHA256/compilação conferidos. SHA256:
971bcb98e8abdc77d73eec50f928b5280d9a106be5bda9075c21396f1fdeeaea.
Suíte completa: 464 aprovados / 3 ignorados. Após teste adicional do wrapper v7,
os 4 testes de wrappers passaram; Ruff aprovado. Build e implantação posteriores
confirmados pelo operador conforme recibo acima.

Solicitação do usuário: consumir duração observada e estimada no mesmo par de
colunas, incluindo horas corridas e úteis. Contrato sla-consolidado-analise-v7.
Campos: duracao_analise_horas, duracao_analise_horas_uteis, origem_duracao_analise,
versao_regra_duracao_analise. Tipos/semântica no PRD e contrato gerado do produto.

Prioridade: observada_validada -> estimada autorizada -> indisponivel/NULL.
Não usar durações observadas reprovadas nem incluir duração de terminal. Zero
útil observado permanece zero. Ambos os valores vêm da mesma origem, sem misturar
horas corridas observadas com úteis estimadas. Todo campo é revalidado no diário.

Preserva integralmente campos anteriores, exceto versao_contrato. Não modifica
fontes, estimativas v6 nem KPI estritamente observado. Nenhuma tabela adicional.
Calendário inalterado: seg-sex 10–13/14–19, São Paulo, BR PUBLIC e extras
configurados; Carnaval/Corpus Christi não são automaticamente descontados.

## Reconciliação local

Base v6: daba7914c4ccbcf8f6d7d60c1b97e2bce742a62a86b379690a89b48cca069bef.
Candidata v7: 105d2939e451dc7368af0c4930f9a919d730588ac5c69aed36123f0c7da577a1.
9.648 linhas / 2.209 projetos; 6.418 valores unificados = 6.227 observados
validados + 191 estimados; 3.230 indisponíveis. Mudanças em campos protegidos: zero.
Reproduzir com tabelas/monday_sla_orcamento/scripts/validate_analysis_upgrade.py.
Base local reconstruída a partir de snapshot com checksum e políticas conferidas;
o plano remoto exige o fingerprint v6, não presumir que a agenda não avançou.

## Implantação controlada

1. Conferir ZIP, extrair em diretório novo e migrate_analysis_contract.py plan.
   Não modifica GCP. Se fingerprint divergir, auditar nova publicação, não forçar.
2. Build, teste de contrato/campos, push e registrar digest imutável.
3. Pausar apenas pipeline-monday-diario. Job pipeline-monday na imagem nova em
   modo plan,--manifest,/app/pipelines.json; manter todas as demais configurações.
4. migrate_analysis_contract.py apply --expected-generation <plano>
   --expected-image <digest>. Exige escritor parado, agenda pausada, base e CAS.
5. Executar daily, confirmar publication_verified e schema/contagens v7 no BQ.
6. Retomar agenda e observar próxima execução automática. Não repetir migrações
   antigas incluídas no ZIP como biblioteca. Não apagar controles/locks ou usar ALTER.

## Consumo

sql/duracao_unificada.sql apresenta ambas as medidas e a origem. Para indicador
com estimativa, informar quantidade/percentual estimado e denominador. Para KPI
estritamente observado continuar usando sla_etapa_horas_uteis. Não anunciar as
duas populações como o mesmo indicador. Não aprova SLA total entre ambientes ou ML.
Campos duracao_horas/uteis anteriores permanecem evidência; não houve mudança
silenciosa de sua semântica. Preferir o novo par de análise no relatório do usuário.
