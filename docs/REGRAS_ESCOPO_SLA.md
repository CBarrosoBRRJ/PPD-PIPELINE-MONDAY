# Escopo de consumo SLA — escopo-sla-v3

Implementação única: compartilhado/src/monday_comum/escopo_sla.py.
Aplica às três tabelas SLA; não altera monday_log_viu2 nem cria tabela de excluídos.
IDs, datas e durações de registros mantidos não mudam por causa do filtro.

## Título

Qualquer posição: UPFRONT; SEM MARCA; MARCA EM SIGILO; MARCA NAO REVELADA;
MARCA A DEFINIR; CURADORIA; MIDIAKIT; MIDIA KIT; LEVOP; ANALISE DAS REDES.
Somente no início, ignorando colchetes de abertura/espaços: PACOTE como palavra,
não PACOTEX. Não exclui [Seara] Bia Reis_ Pacote Rock in Rio nem [Unilever] Pacote
Efeméride. Marca preenchida como Sem Marca não aciona a regra se o título não
contiver o termo. Comparação sem caixa/acentos, espaços repetidos normalizados.

## Tipo de Input

Deny-list exata: ViU First e Proativo. Ignora caixa e espaços nas bordas/repetidos.
Mercado, Inbound, ViU, Interna, Globo, OTR, outros valores e vazios entram.
Não é uma allow-list. A coluna é localizada pelo título Tipo de Input; ambiguidade,
coluna ausente ou célula não recuperada não equivalem a vazio confirmado.
Na origem diária, coluna ausente/ambígua bloqueia o lote. Cadastro ou célula
ausente por projeto exclui todas as passagens desse projeto, sem bloquear os
demais. Status com índice e texto vazio é resolvido pelos labels do schema;
índice sem rótulo recuperável também exclui o projeto. JSON malformado e outros
erros inesperados continuam bloqueando; não são convertidos genericamente em exclusão.

## Aplicação e tempo

Excluir todas as passagens do item nativo. Globocorp usa o cadastro coletado;
alterações posteriores de título/input são reavaliadas na próxima reconstrução.
Viu2 usa cadastro capturado no resgate, não atribuição histórica inventada.
Na consolidação, uma exclusão histórica comprovada se propaga ao par selecionado;
itens ausentes da Gold corrente não são reinseridos. Nada é unido apenas por nome.

Por decisão explícita do usuário, os 300 projetos do SLA histórico sem contexto
de Input recuperado ficam fora do SLA histórico e seus pares ficam fora da
consolidada. Cadastro ausente não equivale a Input vazio: vazio comprovado entra.
A origem globocorp continua sujeita às verificações do seu próprio cadastro.
Esse recorte reduz cobertura; não comprova a correção dos demais dados nem aprova
KPIs. Não apaga fontes e não cria tabela/lista persistida de excluídos.

## Impacto local nas capturas verificadas

| Tabela | Passagens antes | Passagens depois |
|---|---:|---:|
| monday_sla_orcamento_viu2 | 17.486 | 14.761 |
| monday_sla_orcamento_globocorp | 4.237 | 3.453 |
| monday_sla_orcamento | 11.252 | 9.638 |

Excluídos por título/input ou ausência de contexto: 992 itens viu2 e 552 globocorp, contagens por origem
não somáveis como projetos únicos. Consolidada: 2.209 projetos no ensaio.
Captura de cadastro globocorp posterior ao corte da Gold: diagnóstico de impacto,
não nova publicação nem contagens garantidas da próxima execução GCP.
São 300 itens sem contexto no histórico (434 passagens) e 29 na captura local
globocorp (45 passagens). A captura globocorp não é contemporânea da Gold; esses
29 não comprovam ausência no estado diário. Na coleta real, contexto ausente
exclui o projeto em vez de ser silenciosamente tratado como vazio (correção v6).
Os 300 históricos já não participavam da consolidada neste ensaio; seu total
permanece 9.638 passagens. A exclusão do par é testada para as próximas execuções.
Reproduzir com python compartilhado/scripts/avaliar_escopo.py.

## Sequência de implantação (histórico; concluída em 23/09)

Recibos atuais em ESTADO_GCP_2026_09_23.md: histórico filtrado, replay v6 e
consolidada publicados. A sequência abaixo não deve ser repetida como pendência.

Atualizar a tabela histórica uma vez com o recorte tratado e reconciliação integral;
implantar a nova imagem; reconstruir/publicar globocorp com a política atual;
então consolidar. O worker bloqueia origem cuja versão de regras ainda é antiga.
Definir VIU2_ARCHIVE_PREFIX após confirmar o prefixo do resgate já existente no
bucket dedicado. Leitura do contexto histórico exige checksums fixados.
Não executar o ZIP v4 antigo. Não prometer que uma agenda habilitada aplicou regras.

O estado técnico existente ainda é necessário para atualização e recuperação.
Retirar arquivos brutos/GCS dessa arquitetura exige uma migração separada; não
apagar fontes, controles ou locks junto da reorganização de pastas.
