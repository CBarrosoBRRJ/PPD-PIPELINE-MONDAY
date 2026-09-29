# Revisão técnica da v19 — 28/09/2026

## Conclusão

Foram reproduzidos quatro problemas em cenários locais controlados. Nenhuma correção foi aplicada ao pipeline e nenhuma operação foi executada no GCP nesta revisão. A incidência e o impacto quantitativo na publicação real ainda precisam ser reconciliados.

Prioridade sugerida: corrigir a classificação de retrabalho antes de homologar esse indicador; depois tratar a série diária e a associação de duplicados.

## Achados

### 1. P1 — Uma pausa após a entrega é contada como retrabalho e pedido de ajuste

**Local:** [modelo_v19.py:445](../tabelas/monday_sla_orcamento/src/monday_sla_orcamento/modelo_v19.py#L445) e [modelo_v19.py:515](../tabelas/monday_sla_orcamento/src/monday_sla_orcamento/modelo_v19.py#L515).

**Reprodução:** Entrada → Em Elaboração → Aguardando Feedback → Standby, sem qualquer retomada de trabalho depois da entrega.

**Resultado atual:** `quantidade_retrabalhos = 1` e `desfecho = pediu_ajuste`. O núcleo abre um novo ciclo também para `standby`, `espera_marca` e `desconhecido`, e classifica a próxima ação não terminal como ajuste. Isso contraria R4, que exige volta para Entrada, Elaboração ou Revisão.

**Impacto:** pode inflar retrabalho e pedidos de ajuste, além de contaminar a referência de resposta do cliente usada nos alertas. Não foi calculado quantos registros reais são afetados.

**Correção proposta:** só confirmar um novo ciclo de retrabalho quando houver retomada de uma categoria de trabalho; tratar pausa e estado desconhecido explicitamente. A classificação comercial de uma pausa não deve assumir que houve solicitação do cliente. Reconciliar os indicadores derivados após a mudança.

### 2. P2 — Evento à meia-noite aparece no fechamento do dia anterior

**Local:** [modelo_v19.py:634](../tabelas/monday_sla_orcamento/src/monday_sla_orcamento/modelo_v19.py#L634) e [modelo_v19.py:647](../tabelas/monday_sla_orcamento/src/monday_sla_orcamento/modelo_v19.py#L647).

**Reprodução:** primeira entrega em `03/09/2026 00:00 America/Sao_Paulo` (`03:00 UTC`).

**Resultado atual:** a linha de `02/09` já informa `Aguardando Feedback` e uma entrega. As comparações `<= end_of_day` incluem o instante inicial do dia seguinte, enquanto a duração usa um limite exclusivo.

**Impacto:** antecipa status e entregas na série diária; pode introduzir informação futura em análises ou modelos que usem o fechamento do dia. O intervalo D+1 descrito no PRD exclui eventos exatamente no corte.

**Correção proposta:** usar intervalos diários com início inclusivo e fim exclusivo; distinguir o limite de fechamento diário do instante de encerramento definitivo do projeto. Cobrir o caso de meia-noite com teste específico.

### 3. P2 — A série diária termina quando o projeto entra em Standby

**Local:** [modelo_v19.py:627](../tabelas/monday_sla_orcamento/src/monday_sla_orcamento/modelo_v19.py#L627).

**Reprodução:** Entrada em 01/09, Standby em 02/09 e corte em 28/09 às 00h locais.

**Resultado atual:** `monday_sla_projeto_diario` termina em 02/09. Não existem linhas de 03/09 a 27/09, embora o projeto continue parado. `parado_standby` não pertence a `OPEN_STATES`, por isso o limite vira o início do último status.

**Impacto:** a série diária perde os dias de pausa e sub-representa projetos parados. A tabela específica de Standby continua calculando a idade, mas não corrige a lacuna da série destinada à evolução diária e previsão.

**Correção proposta:** separar “fora da fila ativa” de “trajetória encerrada”; manter os dias em Standby até o corte, sem acrescentar trabalho ao orçamento. Confirmar essa semântica da série diária antes da alteração.

### 4. P2 — Vínculo de duplicado escolhe o primeiro candidato mesmo quando há ambiguidade

**Local:** [modelo_v19.py:657](../tabelas/monday_sla_orcamento/src/monday_sla_orcamento/modelo_v19.py#L657).

**Reprodução:** dois projetos originais com o mesmo nome-base e um item duplicado com sufixo `[novo escopo]`, todos com IDs distintos.

**Resultado atual:** `projeto_relacionado = original-a`, por ser o primeiro elemento de `others`, sem evidência adicional que o diferencie de `original-b`.

**Impacto:** associação incorreta na tabela de estudo de duplicados; a ordem de entrada pode mudar o vínculo. O item continua fora do SLA, portanto o efeito direto está na linhagem e no estudo, não no total de orçamento.

**Correção proposta:** vincular automaticamente apenas quando existir um único candidato elegível, preferencialmente com mapa explícito de origem. Nos demais casos, manter o vínculo nulo e registrar a ambiguidade para revisão.

## Melhorias para avaliar

| Prioridade | Melhoria | Benefício / decisão necessária |
| --- | --- | --- |
| Alta | Reconciliar os quatro casos com uma cópia local dos insumos de produção | Quantificar o efeito antes de aprovar nova publicação; não corrigir linhas isoladas no BigQuery |
| Alta | Acrescentar cenários de transição e limites temporais aos testes oficiais | A suíte atual não cobre as quatro reproduções desta revisão |
| Média | Atualizar PRDs e guias para apontarem claramente à v19 | Há documentos normativos que ainda abrem com v18, v12 e “única tabela”; aumenta o risco de operar seguindo instrução antiga |
| Média | Tornar a inicialização retomável após falha parcial | `initialize()` cria todas as tabelas antes de gravar o controle; se falhar no meio, uma nova tentativa recusa as tabelas já criadas. Planejar journal de inicialização; não reexecutar esse comando em produção agora |
| Média | Explicitar o nome da medida mensal | `tempo_orcamento_p50_horas_uteis` mensal usa `tempo_ate_primeira_entrega_horas_uteis`; documentar como primeira entrega ou criar medida distinta para o total com retrabalho, após decisão de negócio |
| Baixa | Endurecer a validação v19 | Rejeitar durações negativas, cortes divergentes e relações entre ciclo e projeto incompatíveis, além de schema e chaves; manter teste de falha sem escrever na nuvem |

## Evidências e limites

- Inspecionados: núcleo e contratos executáveis v19, publicação e recuperação, transação compartilhada, integração no worker consolidado, coordenação, testes relacionados e documentação de implantação.
- `test_modelo_v19.py` + `test_modelo_publication.py`: **20 passaram**.
- Quatro testes adicionais de comportamento esperado: **4 falharam**, reproduzindo os achados acima. São testes locais de auditoria; não foram incorporados à suíte nem usados para alterar produção.
- Orquestração, ensaio de ciclos e manutenção: **25 passaram**. Total da suíte existente executada: **45 passaram**. [Resultados](revisao_v19_20260928/resultados.json) e [reproduções](revisao_v19_20260928/test_reproducao.py).
- A revisão é focada nos caminhos atuais da v19; não constitui auditoria exaustiva de todos os módulos históricos, infraestrutura ou permissões reais.
- Nenhum resultado local foi tratado como prova de incidência em produção. A primeira execução automática de 29/09 deve ser conferida separadamente pelo operador, conforme o recibo do projeto.

## Próxima decisão

Aprovar quais achados devem virar correções, definir a semântica da série em pausa e autorizar a preparação de um pacote local com testes e comparação antes/depois. Qualquer implantação corporativa permanece a cargo do operador autorizado.

## Avaliação e correção — 28/09/2026

Os quatro achados foram confirmados no código e aplicados localmente como regra `modelo-v19-2`. Os IDs de ciclo continuam estáveis (`ID_SEED = modelo-v19-1`). Nada foi publicado no GCP.

| Achado | Incidência na publicação de 28/09 (consulta só de leitura) | Correção |
| --- | --- | --- |
| 1. Pausa vira retrabalho | 5 de 102 `pediu_ajuste` com status seguinte fora de trabalho; 3 ciclos de retrabalho sem passagem de trabalho | Só `trabalho` abre ciclo. A resposta do cliente usa a próxima ação decisiva (trabalho, entrega ou terminal); pausa sem ação posterior vira `pausado`, que não conta como resposta. Espera de marca e Standby do projeto somam todas as passagens válidas. |
| 2. Meia-noite | 0 passagens exatamente às 00:00 locais (preventivo) | Dia com início inclusivo e fim exclusivo; projeto encerrado termina a série no dia do encerramento. |
| 3. Série em Standby | 90 projetos em Standby | `parado_standby` segue até o corte, sem somar trabalho; último dia com `situacao_no_dia = parado_standby`. |
| 4. Duplicado ambíguo | 18 duplicados; nenhum ligado a outra cópia | Vínculo só com um único original elegível (que não seja cópia); caso contrário, nulo e erro `duplicado_original_ambiguo`. |

As quatro reproduções agora passam, e seis testes de regressão entraram em `test_modelo_v19.py`. Suíte completa: 654 passaram, 3 foram ignorados.

Melhorias da tabela acima ainda não implementadas:
- **Medida mensal:** renomear ou documentar `tempo_orcamento_p50_horas_uteis` exige decisão de negócio.
- **Inicialização retomável:** não há reexecução prevista.
- **PRDs antigos e validação reforçada:** ficam no backlog.
