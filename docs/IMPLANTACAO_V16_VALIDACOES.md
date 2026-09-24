# V16 — validações contínuas

Pacote preparado localmente; NÃO implantado. Código-base Git: `2cc432a`.
Produção informada pelo operador: v15, contrato sla-consolidado-talentos-v9.
Não executar novamente migrate_talent_contract.py: não há mudança de contrato,
mapa, schema, população ou calendário nesta versão.

- ZIP: runtime/pipeline-monday-release-20260924-v16-validacoes.zip
- SHA256: 496ebcf1ce99004266dfe3d6e9ad79fe23b7ccd4afcf19d6ad616fa50cb00a62
- 101 arquivos de fontes/configuração mais inventário; hashes internos conferidos.
- Testes da alteração: 550 aprovados, 3 pulados; Ruff aprovado.

## Procedimento

1. Enviar o ZIP ao /home/caio_barroso no Cloud Shell, conferir SHA256 e extrair
   em diretório temporário exclusivo. Submeter Cloud Build com --async e tag
   v16-20260924. Nenhuma alteração de job/tabela ocorre neste passo.
2. Conferir SUCCESS e digest do build. Antes de trocar imagem, conferir estado
   do Scheduler e ausência de execução em andamento. Manter agenda pausada.
3. Atualizar apenas pipeline-monday, us-central1, usando digest verificado,
   comando pipeline-monday e argumentos daily,--manifest,/app/pipelines.json.
4. Executar uma vez e consultar logs filtrados pelo nome exato da execução.
5. Conferir publicação dos produtos, contrato v9 e auditorias SQL existentes.
   No relatório privado da nova geração verificar coverage_audit.balanced e
   cobertura por origem. Não exigir contagens antigas para fontes dinâmicas.

A conferência de cobertura executa em cada construção. Se o conteúdo final
for idêntico ao ativo, o publicador pode retornar skipped: ele não grava um novo
report de geração nessa situação. Não confundir report antigo com esta execução.

Só retomar agenda após conferência. Alertas externos e revisão de identidades
continuam pendentes; este pacote não aprova novos vínculos nem recupera eventos.
Falha de reconciliação bloqueia antes da publicação; não relaxar a validação.
