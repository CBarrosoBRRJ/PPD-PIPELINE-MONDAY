# Auditoria de cobertura dos vinculos — 24/09/2026

Somente leitura das fontes arquivadas e geracao de artefatos privados locais.
Nenhum mapa ou dado GCP alterado. Nao classificar itens sem mapa como nativos
novos: ausencia de vinculo nao prova ausencia de migracao.

## Evidencia reproduzida

- Mapa local: SHA256 486845629229aaa881c38ab87d58cec49811f539642d413d9aa29f07569399eb,
  igual ao hash fixado no publicador e no controle informado pelo operador.
- 4.294 pares selecionados; contexto de 4.368 itens ViU2 e 4.789 Globocorp.
- 74 itens ViU2 nao selecionados (9 conflitos de links e 65 sem nome+data unicos).
- 495 itens Globocorp nao ligados no contexto arquivado; nao e contagem atual.
- Matching recalculado com contextos verificados por SHA; 6.348 candidatos.
- Entre pares nao selecionados, com ambas as pontas livres: 12 possuem link unico
  coincidente e sem conflito de links; 11 tambem possuem nome igual.
- Isso sugere casos para revisao, NAO 12 projetos recuperados/aprovados. Pasta
  compartilhada pode corresponder a mais de uma demanda; validacao de negocio
  e ausencia de conflito de identidade continuam necessarias.

Politica selecionada atual exige nome+Data de Entrada unicos, sem conflito de
links; Data de Entrada cadastral NAO e evento de entrada em status. Reutilizar
mapa para reunir evidencias nao preenche movimentos perdidos nem aprova duracoes.

## Evidencia BQ fornecida pelo operador

Origem completa: 291 passagens Entrada, 45 sem data (246 datadas).
Projetos presentes na consolidada: 10 Entradas na origem, todas sem data.
Consolidada Globocorp: 237 passagens, nenhuma Entrada; KPI de precificacao sem
ciclo aprovado. Comparacao ainda nao separava projetos mapeados excluidos por
outras regras daqueles realmente sem mapa. Nao atribuir todos os 246 ao mapa.

`scripts/audit_identity_coverage_cloudshell.py` faz essa separacao com o mapa
publicado verificado e consulta BQ somente leitura (limite 1 GiB, sem cache).
Nao grava tabelas/objetos, nao consulta Monday nem usa credenciais no arquivo.
Retorna contagens por grupo e IDs sem mapa com Entrada datada para cruzamento
com candidatos privados. Exige controle estavel, sem pending e hash esperado.

## Proximos passos

### Cruzamento posterior com a saída do operador

A auditoria retornou 227 IDs Globocorp sem mapa com Entrada datada. Na captura
arquivada há 207 desses IDs; 20 exigem contexto atualizado. O matching arquivado
contém 23 pares candidatos para 16 dos 227 IDs.

Filtrando esses pares por nome igual, marca coincidente e coincidência da coluna
de talento exclusivo ou interveniência, restam 6 pares/6 IDs Globocorp. Cinco
têm conflito de links; três apontam para uma ponta ViU2 já ocupada no mapa
(grupos podem se sobrepor). Não aprovar nenhum desses casos automaticamente.

Resta um candidato sem esses impedimentos: ViU2 12959570080 ↔ Globocorp
12965547192. Há divergência no campo cadastral Data de Entrada e nenhuma
evidência de link único. Exige revisão de negócio; não foi incorporado ao mapa.
Essas contagens são de candidatos da captura histórica, não de vínculos
comprovados nem de toda a população atual. Conferência contínua documentada em
`VALIDACOES_CONTINUAS_SLA.md`.

Executar auditoria no Cloud Shell autorizado, cruzar os IDs relevantes com o
matching e verificar contexto atual quando necessario. Nao substituir projetos
existentes, ampliar mapa automaticamente por nomes ou alterar filtros de titulo,
Input e talentos. Projetos excluidos pelas regras aprovadas permanecem excluidos.
Novo mapa exige evidencia, politica aprovada, preservacao de IDs existentes,
hash e migracao controlada antes da publicacao. Agenda ainda pausada conforme
ultimo recibo; homologacao operacional e alerta externo permanecem pendentes.
