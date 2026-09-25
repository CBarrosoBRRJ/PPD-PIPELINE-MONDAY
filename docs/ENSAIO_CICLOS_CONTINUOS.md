# Ensaio de ciclos continuos — 25/09

Estado: motor e contrato local implementados, sem publicacao nova. Nao e release
de producao; nenhuma tabela/agenda/job deve ser alterada com este pacote.
O ensaio reconstroi a populacao completa selecionada pelas regras atuais antes
da separacao v17, com fontes GCS verificadas por checksum e cadastro atual.
Nao escreve GCS/BQ; usa SELECT faturavel limitado a 1 GiB, leitura GCS/BQ e
consulta da configuracao do job apenas para prefixo nao secreto do arquivo ViU2.
Nao recupera pendencias, nao adquire lock de escrita. Confere controles/etag
antes/depois; se houver atualizacao concorrente, falha e deve ser repetido.

## No Cloud Shell (apos upload do ZIP de ensaio)

```bash
(
set -euo pipefail
cd /home/caio_barroso
echo 'd83cb90d88b6d9b7fda0a2488740a8370fdbb40aa70443dd429103640bff2356  pipeline-monday-ciclos-ensaio-20260925.zip' | sha256sum -c -
MONDAY_CICLOS_DIR=$(mktemp -d /home/caio_barroso/monday-ciclos-ensaio-XXXXXX)
unzip -q pipeline-monday-ciclos-ensaio-20260925.zip -d "$MONDAY_CICLOS_DIR"
cd "$MONDAY_CICLOS_DIR"
python3 -m venv .venv-ensaio
.venv-ensaio/bin/python -m pip install --quiet \
  ./compartilhado ./orquestracao \
  ./tabelas/monday_sla_orcamento_globocorp ./tabelas/monday_log_viu2 \
  ./tabelas/monday_sla_orcamento_viu2 ./tabelas/monday_sla_orcamento \
  ./tabelas/monday_backlog_agenciamento_2026 ./tabelas/monday_talentos_exclusivos
.venv-ensaio/bin/python scripts/rehearse_live_cycles_cloudshell.py
)
```

Conferir SHA256 fornecido junto do pacote antes de extrair. Requer Python>=3.11
e permissoes de leitura de fontes e execucao de query ja usadas na operacao.
Nao solicita senha Monday e nao altera IAM. Dependencias instaladas em venv
isolado dentro do diretorio temporario; nao interfere no ambiente do job.

Esperado: cycles_rehearsal_only, data_modified=false, contagens de projetos,
ciclos por situacao, estimativas e entregas observadas. publication_verified=false
e intencional: nao houve publicacao. Nao tratar conteudo como tabela pronta para BI.
Colar somente recibo de contagens; nao colar configuracao bruta do job/segredos.
