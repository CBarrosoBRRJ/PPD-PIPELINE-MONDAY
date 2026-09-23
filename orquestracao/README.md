# Pipeline Monday — coordenador geral

Implementação inicial local; **não implantada**. Não cria tabelas, buckets ou agendas.
Executa somente produtos registrados, sequencialmente, cada um em um processo separado.
O filho termina antes de iniciar o seguinte; não há acúmulo das estruturas de dados
Python de todos os produtos no coordenador. Limite de memória ainda exige medição.

## Uso na raiz

```powershell
python -m pip install -e ./orquestracao
pipeline-monday plan --manifest orquestracao/pipelines.example.json
```

`plan` valida a configuração sem acessar GCP/Monday. `daily` é uma operação real:
não executar sem validar o arquivo de ambiente, destino, bucket/estado e agenda.
O exemplo exige `.env.gcp` privado e não o cria nem assume sua configuração.
Produto SLA precisa estar instalado separadamente (`./tabelas/monday_sla_orcamento_globocorp`).

O manifesto é código revisado sem segredos; caminhos são relativos ao diretório
de execução. Não mudar o destino de um checkpoint existente simplesmente editando
o ambiente. Cada produto precisa de configuração, tabela e prefixo próprios.

## Garantias implementadas e limites

- Valida todo o grafo antes de executar; bloqueia ciclos, dependências ausentes,
  IDs repetidos, ambiente compartilhado por produtos e executores não cadastrados.
- Não aceita comandos de shell no manifesto. Somente adaptadores revisados no código.
- Mantém referência de agendamento única e limite global de duração (até 3300s),
  compatível com o timeout de 3600s atualmente configurado. Novos produtos exigem
  revisar duração total, quotas, memória e custos; não há escala ilimitada.
- Falha/skip de origem bloqueia dependentes. Independentes continuam; falha parcial
  retorna código não zero. Todos skipped retornam zero com status explícito skipped,
  nunca significando nova publicação.
- Logs estruturados por produto e sumário geral; sem capturar logs inteiros em memória.
- SLA só informa sucesso após recibo do pipeline, verificação da publicação real e
  reconciliação das passagens/corte. Cada produto continua com seus locks/checkpoints.
- Não há transação atômica envolvendo todas as tabelas nem snapshot comum entre
  produtos. Consumidores cruzados precisarão de contratos de versão/fechamento.
- Timeout mata o processo filho e pode deixar lock. Nunca apagar automaticamente:
  confirmar executor encerrado e reconciliar pending antes de desbloquear geração.
- Histórico viu2 não tem adaptador de escrita diária: não é recalculado pela agenda.
  Um futuro consolidado poderá lê-lo, com versão/hash explícitos.
- Apenas o adaptador do SLA existente está implementado. Não há consolidação de
  contas nem novos produtos habilitados por este coordenador.

## Implantação pendente

Empacotar e validar o coordenador com a imagem e dependências de cada produto,
revisar IAM/destinos e trocar exclusivamente o alvo da agenda do Pipeline Monday.
Não implantar dois escritores. Não alterar LIA. O job remoto ainda é pipeline-orcamento.
Os 8 GiB não estão homologados para um conjunto desconhecido de produtos futuros.
