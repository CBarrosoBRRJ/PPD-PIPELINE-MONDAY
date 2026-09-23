# Fechamento da primeira entrega Monday

## Atualização v11 — prevalece sobre o histórico abaixo

Publicação confirmada e consumo por etapa disponível. Ver
[entrega atual](ENTREGA_CONSUMO_ATUAL.md) e [recibos](ESTADO_GCP_2026_09_23.md).
Pendentes: observar próxima agenda v11 e revisar/versionar mudanças locais no Git.
SLA total entre contas/ML não pertencem ao escopo aprovado. Não repetir exclusões,
migrações ou ações de infraestrutura descritas como planos nas seções históricas.

## Comprovado

- monday_log_viu2: 133.611 eventos preservados e comparados antes da exclusão do nome anterior.
- Resgate bruto original e complemento no bucket dedicado, com verificações de conteúdo registradas.
- Escritor globocorp migrado para monday_sla_orcamento_globocorp; validate-gold concluído.
- Coordenador pipeline-monday configurado para daily, agenda habilitada às 06h Brasília.
- Rotina antiga pausada. LIA não alterada.

## Implementado e executado localmente, não publicado

Reconciliação de observações; reconstrução que interrompe em lacunas; enriquecimento
por rótulo no evento e cadastro datado; contrato separado de revisão com schema,
chaves determinísticas, validação temporal/horas corridas e úteis, nulos e linhagem.
Exportação de 17.486 linhas privada, relida e validada após serialização gzip.
Manifesto proíbe publicação; zero linhas aprovadas para KPI. Não chamar esse artefato
de monday_sla_orcamento_viu2 pronta. Não criar consolidado por UNION ALL das durações.

A exportação está em runtime/validation/viu2_review_export_20260922_v1; dados privados,
fora do Git. schema e referência de campos gerados por
tabelas/monday_sla_orcamento_viu2/scripts/generate_review_contract_docs.py.

## Evidências externas necessárias

### Atualização: seleção de identidade autorizada pelo usuário

O usuário aceitou a seleção por combinação de campos e a exclusão de pares não
resolvidos da consolidação. A execução local de `freeze_selected_identity.py`
recalculou os candidatos a partir dos contextos conferidos por checksum e fixou
4.294 pares um-para-um em `runtime/validation/selected_identity_20260922_v1`.
São 74 itens do contexto viu2 não selecionados (65 sem combinação única e 9 com
conflitos de links); os dados de origem permanecem preservados. Outros 495 itens
globocorp não estão ligados por essa regra; não presumir que são todos novos.

O mapa tem UUID estável ancorado na identidade nativa viu2, evidências por hash,
regra versionada e qualidade `selected_by_user_accepted_policy`. Não representa
revisão humana individual nem mapa oficial da migração; `sla_approved=false`.
Não foi convertido silenciosamente em registros `approved` do contrato anterior.
Está apenas local, não publicado no GCP. A análise de Encerrado é diagnóstico,
não publicação de SLA. Valores anteriores nos eventos comprovam estados, mas não
suas datas de entrada nem durações.

O mapa oficial da TI abaixo continua sendo evidência preferencial para confirmar
ou corrigir ligações, mas a ausência dele não impede preparar a trajetória dos
pares selecionados, preservando a qualidade da correspondência e as lacunas.

1. Mapa da migração: ID do item viu2 -> ID do item globocorp, ou chave de negócio
   comprovadamente preservada com revisão responsável. Nome e pasta igual só geram candidatos.
2. Instante/fase da transferência de responsabilidade entre ambientes em 03/09/2026,
   com horário/fuso ou regra por projeto. Sem isso não fechar passagens na fronteira.
3. Para rótulos/valores ausentes: exportação administrativa ou evidência da fonte, se
   existir. Caso não exista, registrar indisponibilidade e manter NULL; não bloquear
   indefinidamente a preservação do dado bruto nem afirmar que a lacuna foi resolvida.

A inspeção do log estruturado conferido por SHA256 encontrou 27 alterações de settings
com listas de textos em previous_value.labels/value.labels, sem índices explícitos
nessas listas; 13 delas têm value.labels vazio. Não usar posição na lista como índice
nem interpretar vazio automaticamente como remoção de todos os status. O evento de
criação de coluna não traz os rótulos. Essa evidência não basta para preencher os 287
rótulos ausentes no início das passagens.

## Portões técnicos restantes

- Aplicar regras de elegibilidade de Marca/Talento/responsabilidade e validar atributos
  antes de tornar o contrato de revisão um contrato de consumo homologado.
- Aprovar contrato de consumo versionado que preserve início conhecido com fim
  desconhecido. O atual exige horas em toda linha observed; não forçar zeros/cortes.
- Validar amostras e denominadores por origem, limites e lacunas na consolidação.
- Confirmar publicação do novo coordenador e o disparo automático da agenda; execução
  skipped não é publicação. Não zerar reserva diária para aparentar sucesso.

## Limpeza controlada do GCP

Não há comando de exclusão automático nesta entrega. Antes de remover:

| Recurso legado | Condição |
|---|---|
| backup_sla_orcamento_pre_migracao_20260921 | Preservar dados e metadados no GCS privado do pipeline, verificar recuperação/conteúdo e dependências; só então excluir do BQ. Decisão posterior do usuário: não criar dataset BQ de backups |
| sla_orcamento | Verificar dependências e substituto; não confundir com consolidado |
| pipeline-orcamento e agenda antiga | Novo job publicado e agenda validada; preservar configuração e plano de recuperação, sem executar o escritor antigo incompatível |
| Bucket antigo de orçamento | Inventário/reconciliação de objetos e versões, ausência de dependências ativas e cópia recuperável |

Cloud Build, estados Terraform e recursos LIA não são lixo por não serem tabelas.
Não renomear nem excluir recursos compartilhados. Bucket não se renomeia por troca
de rótulo: qualquer migração de dados exige destino e dependências verificados.

## Mensagem honesta para TI

"O histórico disponível pela API do quadro viu2 18393336134 foi resgatado e preservado
no GCP, incluindo uma conferência complementar. A modelagem do SLA e a ligação com
os itens migrados ainda estão em validação. Precisamos do mapa de IDs da migração e
da referência de horário da transferência; há campos históricos ausentes na API.
Se houver exportação administrativa adicional, favor preservá-la antes da retirada
do acesso. Não estamos afirmando que a API disponibilizou todo o histórico vitalício."
