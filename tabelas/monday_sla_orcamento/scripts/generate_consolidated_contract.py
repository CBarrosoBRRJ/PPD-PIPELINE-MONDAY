"""Generate schema/DDL and field dictionary from the separate unified contract."""

import json
from pathlib import Path

from monday_sla_orcamento.consolidation import FIELDS, VERSION, schema


def main():
    root = Path(__file__).resolve().parents[1]
    docs = root / "docs"
    sql = root / "sql"
    sql.mkdir(exist_ok=True)
    ddl_types = {"INTEGER": "INT64", "FLOAT": "FLOAT64", "BOOLEAN": "BOOL"}
    fields = [f"  `{name}` {ddl_types.get(kind, kind)}" + (" NOT NULL" if required else "")
              for name, (kind, required) in FIELDS.items()]
    ddl = ("-- Reference only: initial load uses an explicit schema and WRITE_EMPTY.\n"
           "CREATE TABLE `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento` (\n" +
           ",\n".join(fields) + "\n) CLUSTER BY projeto_id, ambiente_origem, item_id;\n")
    (sql / "consolidated_schema.sql").write_text(ddl, encoding="utf-8")
    (docs / "consolidated_schema.json").write_text(json.dumps(schema(), indent=2), encoding="utf-8")
    lines = ["# Contrato consolidado — " + VERSION, "",
             "Uma linha: passagem datada de origem preservada, ligada a projeto selecionado.",
             "A ordem e a entrada são obrigatórias pela validação Python. Ausências não são preenchidas.",
             "Schema independente do contrato globocorp e histórico; não alterar esses destinos.", "",
             "| Campo | Tipo BQ | Obrigatório no schema |", "|---|---|---|"]
    lines.extend(f"| {name} | {kind} | {'sim' if required else 'não'} |" for name, (kind, required) in FIELDS.items())
    lines += ["", "## Semântica de fechamento", "",
              "status_terminal identifica o status daquela passagem, não o estado atual global do projeto.",
              "finalizacao_observada_utc é a entrada no terminal; saída pode continuar NULL.",
              "Durações de linhas terminais são NULL: não são tempo de SLA após encerramento.",
              "registro_origem_json preserva inclusive a duração original, sem alterá-la na fonte.",
              "ciclo_observado_origem é local a ambiente + projeto, não um ciclo completo entre contas.",
              "reabertura_comprovada_origem exige saída anterior igual à próxima entrada na mesma origem.",
              "tempo_ciclo_observado_horas só aparece no primeiro terminal de uma cadeia contínua",
              "iniciada em Entrada comprovada na mesma origem. Não é o SLA vitalício consolidado.",
              "Se houver lacuna, rótulo desconhecido ou sobreposição, não calcular o total dessa cadeia.",
              "Encerrado e os dois Declinados são terminais atuais; Negócio Fechado exige configuração futura.", "",
              "## Limitações de consumo", "",
              "Contrato candidato v9 preserva as regras de etapa e precificação; consultar recibo de implantação;",
              "liberam apenas duração de passagem encerrada por ambiente + status, não total entre contas.",
              "Demais linhas: nao_elegivel_etapa_origem_v1. Continuidade global permanece false.",
              "Elegibilidade é recalculada na validação: calendário, evidência, pendências e durações.",
              "sla_etapa_horas_uteis: FLOAT NULL fora do KPI; zero observado permanece zero.",
              "AVG(sla_etapa_horas_uteis) usa apenas aprovadas; COUNT desse campo dá o denominador.",
              "classificacao_consumo: aprovado_kpi_etapa, encerramento_observado, sem_saida_observada",
              "ou evidencia_insuficiente. Não descreve necessariamente o estado atual do projeto.",
              "motivos_inelegibilidade_kpi_json: lista dos bloqueios calculados, [] nas aprovadas.",
              "versao_regra_kpi identifica a política aplicada automaticamente em cada execução.",
              "Flags genéricas no JSON da origem preservam a revisão original, não anulam a aprovação local.",
              "eh_retorno global é NULL; retorno_observado_origem conserva a informação de cada origem.",
              "Marca/Talento originais viu2 não são apresentados como identidade de negócio normalizada.",
              "A ausência de saída em não terminal não comprova abandono. Não envelhecer viu2 até hoje.",
              "Sem Entrada comprovada, sem mapa, fora da Gold atual ou com ordem ambígua: fora da seleção.",
              "Não usar total global nem treino ML homologado. Indicador cobre apenas população selecionada.",
              "Falha de validação bloqueia carga. Diário usa WRITE_TRUNCATE atômico com schema explícito.",
              "Leitura de contratos v2/v3/v4/v5/v6/v7 permitida para reconciliação; candidato novo exige v8.", "",
              "## Trajetória por projeto", "",
              "quantidade_passagens_projeto: contagem das passagens publicadas por projeto_id; repetida nas linhas.",
              "qualidade_trajetoria: historico_com_limitacoes ou sequencia_observada_sem_lacunas_detectadas.",
              "Nenhuma dessas classes homologa completude vitalícia, SLA total ou treinamento ML.",
              "limitacoes_trajetoria_json: lista de motivos do projeto inteiro, não só da passagem.",
              "eh_ultima_etapa_observada: exatamente uma linha por projeto; não é prova do status atual.",
              "versao_regra_trajetoria: auditoria-trajetoria-v1, calculada novamente em cada execução.",
              "Para qualidade/cobertura de projetos, filtrar eh_ultima_etapa_observada; não somar contagens repetidas.",
              "Para exibir histórico: ORDER BY projeto_id, ordem_etapa. Tabelas BQ não garantem ordem física.",
              "Sem saída permanece NULL; a próxima entrada não fecha automaticamente uma lacuna.",
              "Datas iguais em eventos diferentes não são ordenadas arbitrariamente; projeto ambíguo fica fora.", "",
              "## Estimativa opcional de fronteira", "",
              "saida_estimada_utc/local: próxima entrada Globocorp após passagem ViU2 não terminal sem saída.",
              "Hipótese: permanência no status anterior até a próxima entrada observada, sem etapas intermediárias.",
              "Não é saída observada, limite estatístico nem prova de continuidade entre contas.",
              "duracao_estimada_horas/horas_uteis: calculadas desde a entrada anterior, arredondadas a 3 casas.",
              "Calendário da estimativa identificado em versao_calendario_estimativa; sem aprovação de KPI.",
              "metodo_estimativa: estimada_pela_proxima_etapa_entre_ambientes ou nao_aplicavel.",
              "interval_id_referencia_estimativa identifica a passagem seguinte usada como hipótese.",
              "versao_regra_estimativa identifica a política aplicada. Datas e durações estimadas são NULL",
              "quando não aplicável. Não há coalescência com as métricas observadas/publicadas.",
              "Bloqueios: terminal/desconhecido, saída existente, mesma origem/status, identidade inadequada,",
              "sobreposição, ausência de próxima etapa ou próximo início posterior ao corte.",
              "Não alimentar KPI oficial ou alvo ML com estimativa sem contrato analítico específico.", "",
              "## Duração unificada para análise", "",
              "duracao_analise_horas e duracao_analise_horas_uteis: prioridade à passagem observada validada;",
              "caso contrário, estimativa autorizada de fronteira; demais NULL. Terminal não acumula.",
              "origem_duracao_analise: observada_validada, estimada ou indisponivel; nunca ocultar a origem.",
              "versao_regra_duracao_analise: duracao-analise-v1. Projeção revalidada em cada publicação.",
              "Usar as duas medidas para análise unificada com hipóteses, mostrando participação estimada.",
              "sla_etapa_horas_uteis mantém exclusivamente o KPI observado. Não mudou o calendário.",
              "Não usar duração histórica reprovada só porque duracao_horas foi preservada na linhagem.", ""]
    lines += ["## Precificação v8 — regras preservadas na v9", "",
              "Entrada até primeiro Aguardando Feedback, sem ligar origens distintas.",
              "Revisão conta; Standby e Retorno Marca/Executivo pausam ambas as medidas.",
              "Totais somente na linha entrega_precificacao_observada=true; contar ciclos uma vez.",
              "Contribuições por passagem apenas em ciclos aprovados; pausas têm campos separados.",
              "Lacunas, intervalos não elegíveis, calendário ou rótulo sem evidência bloqueiam KPI.",
              "Sem Entrada ou entrega comprovadas: horas NULL, não zero. Estimativas não entram.",
              "Nova Entrada reinicia tentativa; terminal anterior à entrega encerra sem entrega.",
              "Situação, ID e motivos de ciclo repetidos não devem ser somados como ciclos.", "",
              "## Cadastro atual Globocorp", "",
              "Campos cadastro_atual_ vêm do snapshot diário verificado por item_id_globocorp.",
              "Captura e linhagem explícitas; são atributos atuais, não autores/atributos históricos.",
              "Pessoas e talentos multivalor preservados como JSON STRING; não explodir sem controlar o grão.",
              "Origem ausente/divergente bloqueia o worker produtivo. Não unir talentos por nome.", "",
              "## Talento atual v9 — candidato", "",
              "talento_nome_atual e eh_interveniencia: preenchidos apenas para rótulo único não ambíguo.",
              "FALSE indica coluna Talentos Exclusivos; TRUE indica Interveniência; NULL é desconhecido/ambíguo.",
              "Não certifica identidade nem vínculo contratual. Não substitui talento_nome histórico.",
              "talentos_atuais_json preserva entradas por origem e texto livre sem dividir por pontuação.",
              "situacao_talento_atual explica ausência, multiplicidade ou ambas as origens.",
              "Uma passagem continua uma linha. Não explodir a lista antes de somar durações.", ""]
    (docs / "CONTRATO_CONSOLIDADO.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
