# Candidatos de identidade viu2 / globocorp

Consulta globocorp somente leitura, conta 21453629/quadro 18429499488; token lido
privadamente, identidade confirmada antes da leitura. Paginação concluída e contagem
conferida antes/depois: 4.789 itens visíveis atuais. Contexto viu2 preservado e
verificado: conta 5890468/quadro 18393336134, 4.368 itens. Nenhum ID nativo em comum.
Não houve mutation no Monday, mudança de GCP ou aprovação de correspondência.

Código: historico_viu2/matching.py e scripts/match_projects.py. Evidência privada em
runtime/validation/project_matching_20260922_v3/matching_report.json. Captura reutilizável
com SHA256 em project_matching_20260922_v1/globocorp_context.json.gz; v2/v3 reutilizaram
a mesma captura sem consultar novamente a API. São retratos, não leitura transacional
de toda a operação nem prova de inexistência de itens arquivados/excluídos.

## Resultado

14 colunas compartilhadas comparadas por ID, tipo e título normalizado. 6.348 pares
candidatos abrangem 4.365 itens antigos; três não têm candidato nas regras testadas.
Uma linha de candidato não significa projeto aprovado nem par único.

| Combinação | Pares únicos em ambas as origens | Observação |
|---|---:|---|
| Nome | 4.149 | Nome isolado não prova identidade |
| Nome + Data de Entrada | 4.303 | Resolve 188 casos com nomes repetidos |
| Nome + Data de Entrada + Marca | 3.734 | Exige Marca preenchida; não cobre nomes sem Marca |
| Nome + link da pasta de orçamento | 2.426 | Há pastas repetidas; unicidade deve considerar a combinação |

Data de Entrada refere-se à coluna de negócio `data`, não `created_at` do item novo.
Na combinação nome/data, existem também 12 valores de chave compostos ambíguos,
que não estão nos 4.303 pares únicos. Não confundir quantidade de valores ambíguos
com quantidade de projetos afetados.

Todos os 4.303 pares nome/data coincidem em pelo menos mais um campo compartilhado.
2.465 possuem também evidência de link único em cada origem. Nove pares nome/data
têm divergência em algum link preenchido nos dois lados e precisam de revisão;
campos podem ter sido corrigidos depois, mas isso não deve ser presumido.
Restam 65 itens viu2 sem correspondência única por nome/data. São 74 itens na fila
prioritária ao unir os 65 com os nove conflitos (grupos disjuntos).
Os demais 4.294 são candidatos sem conflito de link detectado, não vínculos aprovados.

Independentemente dessa combinação, 2.474 pares têm nome igual + link único concordante
sem conflito de outros links preenchidos. Grupos se sobrepõem: não somar as contagens.

## Regra recomendada para revisão

Usar nome normalizado + Data de Entrada como busca de candidatos e conferir links,
Marca e demais atributos disponíveis. Normalização só NFC, caixa e espaços: não
remove pontuação, números ou acentos. Valor vazio não é concordância. Status, pessoas,
relações internas e IDs de contas não são usados como atributos estáveis de união.
Combinações de nome + um/dois campos foram avaliadas para as 12 colunas com maior
quantidade de valores coincidentes (mínimo cinco), além das estatísticas individuais.

Após revisão, persistir mapa entre IDs viu2 e globocorp com evidência e projeto_id
estável; não fazer join diário por nome/data mutáveis. IDs originais permanecem.
Campos divergentes e todas as alternativas ficam no relatório privado.
Todas as linhas têm review_status=pending e approved=false. Não alimentar a
consolidação nem somar durações antes de revisão e tratamento da fronteira temporal.

Os 300 itens históricos ausentes do cadastro viu2 não entram neste denominador de
4.368; a cobertura de 98,5% é do cadastro capturado, não de todo o histórico dos logs.
