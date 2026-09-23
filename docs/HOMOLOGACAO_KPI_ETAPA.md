# Homologação do KPI de etapa — candidata local

## Decisão e limites

Em 23/09 o usuário aceitou avançar no tempo por etapa, em horas úteis, separado
por ambiente. Não é aprovação de tempo total entre contas nem de metas de SLA.
Horas úteis medem permanência no expediente, não esforço do responsável.
Política kpi-etapa-origem-v1 em tabelas/monday_sla_orcamento/src/monday_sla_orcamento/kpi_etapa.py.
Integrada localmente ao contrato sla-consolidado-etapa-v3 e à validação anterior
à publicação. Produção permanece v7 de revisão até novo recibo de implantação.
O schema físico não mudou; IDs, datas, durações e população são preservados.
Na v3, filtrar elegivel_comparacao=true e validacao_negocio=aprovado_etapa_origem_v1.
Não interpretar essa flag como aprovação de total entre contas.

## Contrato candidato

- Origem: consolidada v7 reconstruída de artefatos fixados por SHA e contexto
  Input histórico verificado. Grão: uma passagem encerrada, chave interval_id.
- Tempo: horas úteis FLOAT, desconhecido não vira zero. Calendário deve coincidir
  com versão explícita; recalcular horas úteis e corridas e reconciliar três casas.
- Incluir só não terminal com rótulo conhecido, entrada/saída comprovadas,
  evidência histórica dos limites ou elegibilidade já comprovada da origem atual.
- Bloquear mudanças de schema não revisadas, lacunas, sobreposições, rótulos
  ambíguos, calendário desconhecido e qualquer pendência nova não cadastrada.
- Pendências genéricas de revisão/mapeamento/migração não são removidas da fonte.
  Não impedem automaticamente a métrica local, mas continuam bloqueando total global.
- Consumidor: análise de duração por ambiente + status_nome. Não fundir códigos
  de status entre ambientes nem atribuir duração a responsável histórico não provado.
- Mediana/média têm denominador de passagens elegíveis; retornos são passagens
  distintas. Sempre apresentar contagem de projetos e cobertura no mesmo recorte.
- Recorte temporal por saída da passagem, quando houver período de análise.
  O resultado descreve passagens concluídas, não toda a fila ou todos os projetos.
- Fonte consolidada contém somente projetos selecionados com par e presentes
  na Gold atual. Não usar esse subconjunto como indicador de toda a operação.
- Falha: não aprovar linha, nem substituir ausência por duração zero. JSON inválido
  bloqueia auditoria. Esta fase não grava GCP nem muda dados públicos.

## Evidência local inicial

Reprodução: PYTHONPATH=compartilhado/src e Python do ambiente virtual executando
tabelas/monday_sla_orcamento/scripts/audit_kpi_candidate.py --output <relatorio-novo.json>
a partir da raiz.
Arquivos privados de entrada e relatório ficam fora do Git. Script confere hashes.
Reconstrução v7: 9.648 linhas, fingerprint
f0607af6d79deceb251e7a98d99deffd066ecf0a3dda6ab3fdda23fe14adb1ef.

| Ambiente | Passagens no subconjunto | Candidatas | Projetos candidatos |
|---|---:|---:|---:|
| ViU2 | 9.431 | 6.202 | 2.081 |
| Globocorp | 217 | 25 | 13 |

6.227 candidatas de 9.648 linhas (inclui terminais/abertas no denominador).
Projetos de origens diferentes não devem ser somados como pessoas/projetos únicos.
Motivos de bloqueio se sobrepõem; suas contagens não são aditivas.
Calendário auditado work-v1:a8c0c60dacf9dd96: BR PUBLIC, São Paulo,
seg-sex 10–13h/14–19h. Não adicionar Carnaval/Corpus Christi ou feriados locais
sem configuração explícita. Versões diferentes não são aprovadas silenciosamente.

## Portões restantes

Testes locais após política candidata: 389 passed, 3 skipped. Ruff dos três arquivos
novos aprovado. Testes cobrem terminal, ausência de saída/rótulo, schema pendente,
pendência futura, horas divergentes/NaN, zero útil legítimo, falta de eventos e
elegibilidade negativa da origem. Nenhuma publicação ou aprovação remota ocorreu.

1. Concluído: artefato baixado SHA e892c698bf6f5656f47b9beee3e3a0fdb7bb72904de4105d43c1a035eb5f0e6f,
   fingerprint ativo 6c33244f4fff85a9f5ebd0e09685aed8a6bf746eb0f5d8df92e7b91363447987.
   Divergência local apenas na representação de datas do registro_origem_json de
   217 linhas Globocorp; zero diferenças materiais ou de decisão. Não substituir
   o fingerprint registrado pelo hash local. Script reconcile_kpi_snapshot.py reproduz.
2. Evidência local: zero mudanças conflitantes de rótulo no suporte das 17.486
   passagens enriquecidas; manter essa proteção na integração preventiva.
   Não considerar o estado de revisão como certificado de negócio.
3. Concluído localmente: elegibilidade por indicador no contrato v3, bloqueio
   de continuidade global e leitura v2 para reconciliar snapshot ativo na migração.
   Validação sobre artefato publicado: apenas versão, aprovação local e elegibilidade
   mudam. Fingerprint candidato: 89d4c1281e616533c16ba960bf1dfeee0f81432bb2fcf441e1a6b010303a1135.
4. Gerar release/migração, publicar e conferir conteúdo/contagens em BQ.
5. Só então liberar consumo com filtro e denominador documentados.

Não dizer que o KPI está oficial antes desses portões. Terraform legado e GitHub
são pendências de organização separadas; não autorizam apply/destroy ou push.
