# V15 — escopo de talento (contrato candidato v9)

## Recibo local

- Suite: 544 aprovados, 3 ignorados; regra de reinclusao apos correcao testada.
- ZIP source-only: `runtime/pipeline-monday-release-20260924-v15-escopo-talentos.zip`.
- SHA256: `c85838bd6cb015dd0565e1df6f49a8279e2463b9cf3a274f5b4c3dcd24f4c3f4`.
- 100 arquivos de codigo/configuracao mais inventario; sem .env ou dados reais.
- Testes nao substituem homologacao dos dados/alerta no GCP.

Substitui integralmente o ZIP v14 antes de sua implantacao. Producao confirmada
continua v13/v8; nao aplicar v14. Usar migrate_talent_contract.py para migrar v8
a v9 com geração/fingerprint atuais e imagem v15 por digest. Se controle ja
estiver v9, parar e conferir imagem ativa antes de continuar; nao presumir que
o pacote anterior nao foi usado.

## Regra aprovada

Excluir projeto inteiro (todas as passagens ViU2 e Globocorp) se cadastro atual
verificado tiver duas colunas preenchidas, nenhuma preenchida, palavra Squad
ou mais de um exclusivo. Nomes iguais nas duas colunas continuam ambiguos.
Squad detectado como palavra, nao substring. Dados de origem e backlog completos
nao sao apagados. Relatorio privado generations/.../report.json registra projetos,
motivos e contagens. Lote inteiramente vazio continua bloqueado pelo publicador.

## Validacao

O futuro job de correcao do Monday deve terminar antes da captura diaria deste
pipeline. Nao ha lista permanente de exclusao: contexto e elegibilidade sao
reavaliados a cada rodada. Correcao posterior a captura aguarda a rodada seguinte.
A origem SLA usa reserva por dia: repetir daily no mesmo dia pode reaproveitar
a Gold ja verificada; nao prometer replay integral imediato de correcoes no
mesmo dia. Backlog e consolidado precisam de evidencias compativeis.

Reinclusao exige todos os criterios, inclusive mapa de identidade selecionado,
presenca na Gold corrente, historico e filtros de titulo/Input. Item novo sem
mapa nao e automaticamente incluido na consolidada; backlog permanece completo.
O novo job de correcao nao deve alterar diretamente BQ, controles, locks ou
historico deste pipeline. Se captura falhar, conservar publicacao anterior e
sinalizar falha, nunca interpretar como exclusao de todos os itens.

- Preservacao das fontes, exclusao das duas origens e reinclusao apos correcao.
- Sem novas chaves/duracoes; filtros de titulo/Input e precificacao permanecem.
- Falta tecnica de contexto e JSON invalido bloqueiam, sem exclusao silenciosa.
- Comparar contagens antes/depois com relatorio de exclusoes; nao exigir manter
  9.672 passagens quando projetos foram removidos por regra aprovada.
- Consulta auditoria_escopo_talentos.sql deve retornar zero violacoes; executar
  tambem auditoria_cadastro_atual.sql e auditoria_talentos.sql.
- Ainda pendentes: build GCP, migracao, publicacao, auditorias reais, controles
  sem pending, alerta externo e retomada da agenda. Nao declarar entrega integral.

Sequencia operacional identica ao guia V14, mas com ZIP e imagem V15. Nao repetir
migracao v7→v8, nao restaurar imagem v13 sozinha apos migrar controle para v9.
