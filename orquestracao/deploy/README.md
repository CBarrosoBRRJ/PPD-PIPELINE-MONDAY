# Pacote do coordenador

## Candidato v5: organização e escopo-sla-v3

Substitui v4 para os próximos testes. Seis pacotes: comum, log, histórico SLA,
SLA globocorp, consolidação e orquestração. ZIP contém somente código/metadados.
Não implantar sem o preflight e a migração histórica descritos em
docs/ENTREGA_V5_ESCOPO.md na raiz. A agenda existente não aplica esses filtros
até a troca da imagem e a publicação verificadas. Seções abaixo são histórico.

## Candidato v4: consolidação diária (local, não implantado)

Esta seção substitui as descrições antigas de um único produto abaixo. O pacote
agora contém três pacotes Python: SLA corrente, biblioteca histórica e coordenador.
Inclui somente código/metadados, nunca os arquivos privados do histórico ou .env.
O manifesto planeja sla_orcamento e depois monday_sla_orcamento. O histórico não
ganha rotina de coleta: é lido de artefato GCS congelado e fixado por checksum.
O seletor globocorp-runtime herda a configuração de origem, mas o destino e o
controle da consolidação são separados. Não alterar BQ_TABLE do job.

Ver docs/ATUALIZACAO_DIARIA_CONSOLIDADO.md na raiz para contrato, recuperação e
gates de implantação. Teste offline deve listar os dois produtos; isso não é
comprovação de publicação. Preservar imagem anterior e aguardar execução real
antes de retomar a agenda. Não executar comandos de renomeação com este manifesto.

## Histórico das releases anteriores

Execute `python orquestracao/deploy/prepare_release.py --output runtime/pipeline-monday-release-20260922.zip`
na raiz. O diretório de saída deve existir; um ZIP existente nunca é sobrescrito.
O pacote inclui somente os dois pacotes Python, metadados de instalação,
Dockerfile, manifesto diário e inventário SHA-256 por arquivo. Não inclui .env,
histórico viu2, runtime, Terraform, credenciais ou dados de produção.
Não usar a raiz completa do repositório como contexto de build; extrair o ZIP em
diretório novo e usar esse diretório. Dependências seguem os intervalos existentes;
ainda não há lock completo. Registrar o digest da imagem construída para implantação.

A imagem executa `plan --manifest /app/pipelines.json` por padrão, sem acessar GCP
ou Monday. Testar com `docker run --rm --network none IMAGEM`. Para carga real,
os argumentos serão `daily --manifest /app/pipelines.json`; NÃO usar somente daily.
Cloud Run injeta configuração e segredo; `.env` não existe na imagem, e o adaptador
usa o fallback explícito existente para variáveis de ambiente. Apenas um produto
está cadastrado; novos produtos exigem configuração isolada e adaptador revisado.

## Barreiras antes de produção

1. Revisar configuração não secreta e referências Secret Manager do job atual;
   não copiar valores de segredo para este pacote ou para o chat.
2. Publicar uma imagem por digest e criar `pipeline-monday` em modo plan, sem agenda.
3. Preservar identidade de estado, prefixo e tabela legada nessa troca de executor.
   Renomeação BQ exige migração própria; não editar BQ_TABLE isoladamente.
4. Antes de testar daily, pausar somente a agenda antiga, confirmar zero execuções
   ativas e preservar o mesmo lock GCS. Skip diário não comprova nova publicação.
5. Após homologação, trocar para `pipeline-monday-diario`, garantindo uma só agenda
   ativa. Não criar uma agenda ativa antes de desativar a antiga.
6. Rollback de executor exige zero execuções ativas e reconciliação de pending/lock;
   não restaurar estado antigo sobre publicação mais recente.

Sem scripts de exclusão, alterações IAM ou mudanças na LIA neste pacote.
Não executar Terraform. Histórico viu2 não está no manifesto diário.
