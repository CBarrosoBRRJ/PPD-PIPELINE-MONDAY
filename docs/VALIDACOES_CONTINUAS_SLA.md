# Validações contínuas da consolidada

## Estado em 24/09/2026

Complemento local testado; ainda NÃO implantado no GCP. Não modifica schema,
mapa ou regras de KPI. A produção permanece na imagem v15 informada pelo operador.

Cada construção da consolidada já valida schema, chaves, mapa um-para-um,
trajetória, projeções de duração, estimativas, precificação e cadastro/talento.
O worker exige cadastro atual publicado e verificado, sem pendência, e fonte
com o corte solicitado. Essas verificações não provam completude do histórico.

O complemento `coverage.audit` acrescenta ao report privado de cada construção:

- reconciliação: linhas das duas fontes = linhas publicadas + exclusões;
- itens presentes, publicados, mapeados não publicados e sem mapa por origem;
- IDs sem mapa e quantidade daqueles com Entrada datada;
- confirmação explícita de que a auditoria não aprovou novas identidades.

Falha na reconciliação ou item publicado fora da origem/mapa interrompe a
construção antes do publicador. Ausência de vínculo é pendência de cobertura,
não prova de projeto novo e não autorização para união por similaridade.
IDs ficam no report privado, não em logs gerais. Não cria tabela no BigQuery.

As regras de exclusão são reaplicadas, sem lista permanente de bloqueio;
uma correção pode reincluir o projeto quando houver mapa e os demais critérios
forem atendidos. A fonte diária pode reutilizar seu fechamento no mesmo dia.

## Aceite ainda pendente

1. Revisar candidatos de identidade e obter contexto atual para itens ausentes
   da captura arquivada; preservar os IDs dos vínculos aprovados.
2. Empacotar/implantar o complemento e conferir seu report numa execução real.
3. Homologar alerta externo: os logs anteriores indicavam `not_configured`.
4. Confirmar configuração e execução agendada após retomada autorizada.

Verificação local deste complemento: 550 testes passaram, 3 pulados; Ruff nos
arquivos Python alterados passou. Isso não equivale a homologação GCP.
