# Histórico viu2 — carga única

## Responsabilidade atual

Esta pasta constrói monday_sla_orcamento_viu2 (passagens históricas tratadas),
sem coleta diária. Resgate/log pertencem a ../monday_log_viu2 e consolidação a
../monday_sla_orcamento. As seções antigas abaixo documentam a origem do resgate;
os nomes legados nelas não são destinos a recriar.

Primeira carga confirmada: 17.486 linhas. Novo escopo-sla-v3 produz 14.761 linhas
no ensaio, com exclusão dos 300 projetos sem Input verificável. A atualização
remota desse recorte ainda está pendente. Vazio comprovado continua permitido.
Ver ../../docs/REGRAS_ESCOPO_SLA.md e ../../docs/ENTREGA_V5_ESCOPO.md.

Fonte: conta Monday viu2, quadro 18393336134. A conta globocorp e o quadro
18429499488 são outra origem; os IDs não são intercambiáveis.

## Produtos

- Arquivo bruto privado no GCS: respostas originais, metadados, hashes e manifesto.
- log_monday_viu2: tabela histórica estruturada de todos os eventos disponíveis.
- sla_orcamento_viu2: gerador offline de candidato implementado; publicação depende da validação temporal e das alterações em lote.

Não há agendamento. A rotina corrente sla_orcamento continua independente.
Não interpretar a existência deste código como publicação no GCP.

## Resgate

Instale primeiro o pacote de sla_orcamento e depois este pacote, da raiz:

```powershell
python -m pip install -e ./tabelas/monday_sla_orcamento_globocorp
python -m pip install --no-deps -e ./tabelas/monday_sla_orcamento_viu2
python tabelas/monday_log_viu2/scripts/archive_board_logs.py --board-id 18393336134 --source viu2 --expected-account-id 5890468 --output runtime/archives/viu2_18393336134_20260921 --env-file CAMINHO_PRIVADO --curl
```

O arquivo privado usa MONDAY_API_TOKEN; não inserir token em argumentos, Git ou logs.
--curl usa o TLS nativo do Windows com certificado validado e credencial via stdin.
O conteúdo de data permanece intacto. Não há filtro por coluna, status, elegibilidade
ou data de migração. Janelas de sete dias são subdivididas antes de atingir 10 mil eventos.
Páginas persistem antes da próxima chamada; reiniciar no mesmo diretório reutiliza
arquivos validados. Falha mantém status incomplete. Arquivo corrompido nunca é sobrescrito.
Não misturar credenciais, origem, tamanho de página ou versão de API em uma retomada.

complete_available_api_history significa que as consultas terminam e os arquivos
foram validados; não prova que o Monday conservou todos os eventos de toda a vida.
O manifesto declara o intervalo solicitado e a primeira/última evidência retornada.

## Contrato do log estruturado

Origem: páginas aceitas do arquivo acima. Grão: um evento por conta de origem,
quadro e event_id. Sem excluir eventos de colunas diferentes de Status.
Preservar event_at_raw e data_raw STRING; data_raw não deve ser remodelado.
event_at_utc TIMESTAMP e item_id INT64 podem ser NULL quando a interpretação falhar;
o registro bruto continua disponível e a falha é sinalizada.
IDs de origem e de autor continuam STRING; board_id INT64.
Metadados de coleta, arquivo e SHA-256 permitem rastrear cada linha.
Consumidores: reconstrução da SLA e análises futuras. Erro de checksum ou eventos
conflitantes bloqueia a exportação. Publicação futura deve usar WRITE_EMPTY;
nunca WRITE_TRUNCATE em tabela histórica já congelada.

## Regra de análise entre ambientes

A decisão atual é reconstruir a trajetória completa por projeto em uma camada
consolidada, preservando as fontes separadas. Não descartar projetos nem eventos
com base em uma data de migração presumida. O horário exato permanece pendente;
a criação do quadro novo não o comprova. Não criar transição pela cópia do projeto.
Veja [a decisão de continuidade](../../docs/CONTINUIDADE_PROJETOS_MONDAY.md).

As duas SLAs devem ter colunas de negócio compatíveis. Uma correspondência revisada
liga (conta, quadro, item_id) a um projeto integrado para relatórios. Mesmos nomes
produzem candidatos, nunca vínculos automáticos. Passagens que atravessam o corte
exigem reconciliação para não somar duas vezes a mesma duração.

Bucket dedicado pode guardar prefixos separados de arquivo e execução corrente.
Não excluir bucket antigo nem aplicar retenção bloqueada sem inventário e validação.

## Candidato offline do SLA histórico

`scripts/build_sla_candidate.py` exige `--archive`, `--output` novo e `--cutoff`
ISO-8601 com hora e fuso. O limite é exclusivo e precisa de validação de negócio:
não usar automaticamente a coleta de setembro como saída de passagens abertas
na migração. O script não acessa Monday/GCP, não agenda e não sobrescreve saídas.

Verifica hashes, origem e contagens antes de reutilizar as regras de SLA/hora útil.
Gera NDJSON, schema público compatível, calendário, qualidade e manifesto de rascunho.
Datas e durações inferidas continuam NULL na saída. Eventos de status não suportados
são contabilizados como bloqueio de publicação, não silenciosamente considerados cobertos.
O comando não publica: `draft_not_published` nunca significa SLA histórico homologado.
