"""Modelo de consumo v19: uma tabela pronta para cada pergunta de negócio.

Regras (fonte de verdade: nota do projeto no Obsidian, R1–R15 e D1–D3, 28/09/2026):
- Início válido: primeiro status vazio ou Entrada. Entrega sem Entrada antes é erro.
- Ciclo: da Entrada (ou da volta ao trabalho) até o início de Aguardando Feedback.
  Voltar do feedback para trabalho abre ciclo de retrabalho; o tempo soma.
- Tempo de orçamento: só status de trabalho. Standby e "Retorno Marca/Executivo"
  (espera da marca, D1) não contam. Terminal no meio da trajetória é erro de
  preenchimento e é ignorado (D3), mas vai para a tabela de erros.
- Resposta do cliente: cada Aguardando Feedback até a próxima ação. Encerrado ~29
  dias depois é automação do Monday, não resposta.
- Desconhecido nunca vira zero: a soma fica nula e o registro, incompleto.
"""

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid5
from zoneinfo import ZoneInfo

from monday_comum.escopo_sla import motivos_exclusao, motivos_input

from monday_sla_orcamento.pricing import PAUSES, TERMINALS, WORK, normalize
from monday_sla_orcamento.talent_context import POOL, exclusion_reasons as talent_exclusions, is_pool, same_talent

RULE = "modelo-v20-1"  # v19-2: revisão técnica; v20: talento R21–R26, pool, sem Entrada e catálogos (29/09/2026)
# Contrato publicado (esquema das tabelas). Só muda com mudança de esquema: é a identidade gravada no controle
# do GCS. A v20 acrescenta 4 tabelas; a migração a partir de modelo-v19-1 é feita por ModelStore.initialize().
CONTRACT = "modelo-v20-1"
ID_SEED = "modelo-v19-1"  # semente dos IDs de ciclo: mantém os IDs estáveis entre versões da regra e do contrato
ZONE = ZoneInfo("America/Sao_Paulo")
NAMESPACE = UUID("07530d27-26df-4c5f-a2a1-092eb8ef04cf")  # igual à consolidação
FEEDBACK = normalize("Aguardando Feedback")
STANDBY = normalize("Standby")
BRAND_WAIT = PAUSES - {STANDBY}  # "Em elaboração - Retorno Marca/Executivo" (D1)
AUTO_CLOSE_DAYS = range(28, 32)  # automação observada: 913 casos com 29 dias
STANDBY_STALE_DAYS = 30
REFERENCE_MIN_SAMPLES = 15
# Parado em Standby tem tabela própria (D4) e não entra na fila de em andamento.
OPEN_STATES = ("em_orcamento", "em_retrabalho", "aguardando_cliente", "aguardando_marca")
STAGE = {"trabalho": 2, "espera_marca": 2, "entrega": 4, "terminal": 5}

STR, INT, FLT, BOOL, TS, DAY = "STRING", "INTEGER", "FLOAT", "BOOLEAN", "TIMESTAMP", "DATE"


def _fields(spec):
    """'nome:TIPO' ou 'nome:TIPO!' (obrigatório)."""
    result = {}
    for item in spec.split():
        name, kind = item.split(":")
        result[name] = (kind.rstrip("!"), kind.endswith("!"))
    return result


CONTRACTS = {
    "monday_sla_projeto": _fields(
        "projeto_id:STRING! projeto_nome:STRING conta_origem:STRING! item_id_viu2:INTEGER item_id_globocorp:INTEGER "
        "entrada_utc:TIMESTAMP! mes_entrada:DATE! situacao_atual:STRING! status_atual:STRING "
        "primeira_entrega_utc:TIMESTAMP ultima_entrega_utc:TIMESTAMP quantidade_entregas:INTEGER! "
        "quantidade_retrabalhos:INTEGER! tempo_orcamento_horas_uteis:FLOAT tempo_orcamento_horas_corridas:FLOAT "
        "tempo_ate_primeira_entrega_horas_uteis:FLOAT bruto_ate_primeira_entrega_horas_uteis:FLOAT "
        "espera_marca_horas_uteis:FLOAT standby_horas_uteis:FLOAT resposta_cliente_horas_uteis:FLOAT "
        "completo:BOOLEAN! contem_estimativa:BOOLEAN! nasceu_de_copia:BOOLEAN! projeto_relacionado:STRING "
        "marca:STRING talento:STRING eh_interveniencia:BOOLEAN tipo_input:STRING tipo_projeto:STRING "
        "responsavel:STRING corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_ciclo": _fields(
        "ciclo_id:STRING! projeto_id:STRING! numero_ciclo:INTEGER! tipo_ciclo:STRING! inicio_utc:TIMESTAMP! "
        "fim_utc:TIMESTAMP situacao:STRING! trabalho_horas_uteis:FLOAT trabalho_horas_corridas:FLOAT "
        "espera_marca_horas_uteis:FLOAT standby_horas_uteis:FLOAT bruto_horas_uteis:FLOAT "
        "passagens_trabalho:INTEGER! completo:BOOLEAN! contem_estimativa:BOOLEAN! interval_id_entrega:STRING "
        "mes_fim:DATE corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_passagem": _fields(
        "interval_id:STRING! projeto_id:STRING! ordem:INTEGER! status_nome:STRING categoria:STRING! "
        "ciclo_id:STRING conta_no_tempo_orcamento:BOOLEAN! ignorada:BOOLEAN! motivo_ignorada:STRING "
        "conta_origem:STRING! inicio_utc:TIMESTAMP! saida_observada_utc:TIMESTAMP fim_referencia_utc:TIMESTAMP "
        "origem_duracao:STRING! horas_uteis:FLOAT horas_corridas:FLOAT mes_inicio:DATE! corte_utc:TIMESTAMP! "
        "versao_regra:STRING!"),
    "monday_sla_tempo_status": _fields(
        "projeto_id:STRING! status_nome:STRING! categoria:STRING! visitas:INTEGER! passagens:INTEGER! "
        "horas_uteis:FLOAT horas_corridas:FLOAT completo:BOOLEAN! contem_estimativa:BOOLEAN! "
        "corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_resposta_cliente": _fields(
        "interval_id:STRING! projeto_id:STRING! numero_entrega:INTEGER! inicio_utc:TIMESTAMP! "
        "proxima_acao_utc:TIMESTAMP desfecho:STRING! status_seguinte:STRING conta_como_resposta:BOOLEAN! "
        "horas_uteis:FLOAT dias_corridos:INTEGER origem_duracao:STRING! mes_inicio:DATE! "
        "corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_em_andamento": _fields(
        "projeto_id:STRING! projeto_nome:STRING situacao_atual:STRING! status_atual:STRING "
        "no_status_desde_utc:TIMESTAMP! horas_uteis_no_status:FLOAT! numero_ciclo_atual:INTEGER "
        "horas_uteis_desde_entrada:FLOAT! referencia_atencao_horas:FLOAT referencia_critico_horas:FLOAT "
        "nivel_alerta:STRING! responsavel:STRING marca:STRING talento:STRING corte_utc:TIMESTAMP! "
        "versao_regra:STRING!"),
    "monday_sla_referencia_status": _fields(
        "status_nome:STRING! categoria:STRING! passagens_observadas:INTEGER! p50_horas_uteis:FLOAT "
        "p80_horas_uteis:FLOAT p90_horas_uteis:FLOAT referencia_atencao_horas:FLOAT "
        "referencia_critico_horas:FLOAT janela_inicio:DATE! corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_gargalo_mensal": _fields(
        "mes:DATE! status_nome:STRING! categoria:STRING! passagens:INTEGER! projetos:INTEGER! "
        "horas_uteis_total:FLOAT horas_uteis_p50:FLOAT horas_uteis_p80:FLOAT passagens_sem_duracao:INTEGER! "
        "corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_kpi_mensal": _fields(
        "mes:DATE! projetos_iniciados:INTEGER! entregas:INTEGER! projetos_primeira_entrega:INTEGER! "
        "tempo_orcamento_p50_horas_uteis:FLOAT tempo_orcamento_p80_horas_uteis:FLOAT "
        "pct_projetos_com_retrabalho:FLOAT pedidos_de_ajuste:INTEGER! resposta_ajuste_p50_horas_uteis:FLOAT "
        "encerrados_automaticos:INTEGER! decisoes_registradas:INTEGER! erros_preenchimento:INTEGER! "
        "corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_qualidade": _fields(
        "chave:STRING! projeto_id:STRING item_id_viu2:INTEGER item_id_globocorp:INTEGER projeto_nome:STRING "
        "situacao_calculo:STRING! motivos_json:STRING! conta_origem:STRING quantidade_passagens:INTEGER! "
        "corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_erro_preenchimento": _fields(
        "erro_id:STRING! projeto_id:STRING item_id_globocorp:INTEGER projeto_nome:STRING tipo_erro:STRING! "
        "gravidade:STRING! descricao:STRING! status_nome:STRING ocorrido_em_utc:TIMESTAMP mes:DATE "
        "responsavel:STRING conta_origem:STRING corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_qualidade_preenchimento": _fields(
        "mes:DATE! responsavel:STRING! projetos_iniciados:INTEGER! projetos_com_erro:INTEGER! "
        "pct_projetos_sem_erro:FLOAT erros:INTEGER! erros_graves:INTEGER! tipos_json:STRING! "
        "corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_dim_status": _fields(
        "status_nome:STRING! categoria:STRING! conta_no_tempo_orcamento:BOOLEAN! eh_entrega:BOOLEAN! "
        "eh_terminal:BOOLEAN! etapa:INTEGER no_quadro_atual:BOOLEAN! passagens_total:INTEGER! "
        "itens_total:INTEGER! passagens_12_meses:INTEGER! passagens_ano_atual:INTEGER! primeiro_uso_utc:TIMESTAMP "
        "ultimo_uso_utc:TIMESTAMP versao_regra:STRING!"),
    "monday_sla_item_duplicado": _fields(
        "projeto_id:STRING! item_id_globocorp:INTEGER projeto_nome:STRING status_copiado:STRING "
        "entrada_utc:TIMESTAMP! mes_entrada:DATE! status_atual:STRING quantidade_entregas:INTEGER! "
        "primeira_entrega_utc:TIMESTAMP trabalho_horas_uteis:FLOAT trajeto:STRING! projeto_relacionado:STRING "
        "projeto_relacionado_nome:STRING responsavel:STRING marca:STRING corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_standby": _fields(
        "projeto_id:STRING! projeto_nome:STRING em_standby_desde_utc:TIMESTAMP! dias_corridos_parado:INTEGER! "
        "horas_uteis_parado:FLOAT! status_anterior:STRING quantidade_entregas:INTEGER! acima_do_limite:BOOLEAN! "
        "responsavel:STRING marca:STRING talento:STRING corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_dim_calendario": _fields(
        "data:DATE! ano:INTEGER! mes:INTEGER! trimestre:INTEGER! semana_iso:STRING! dia_semana:INTEGER! "
        "eh_dia_util:BOOLEAN! eh_feriado:BOOLEAN! nome_feriado:STRING horas_uteis_dia:FLOAT! versao_regra:STRING!"),
    "monday_sla_projeto_diario": _fields(
        "projeto_id:STRING! data:DATE! status_fim_do_dia:STRING categoria:STRING situacao_no_dia:STRING! "
        "entregas_ate_o_dia:INTEGER! tempo_orcamento_acumulado_horas_uteis:FLOAT "
        "horas_uteis_desde_entrada:FLOAT! eh_dia_util:BOOLEAN! versao_regra:STRING!"),
}
CONTRACTS.update({
    "monday_sla_projeto_pool": _fields(
        "projeto_id:STRING! projeto_nome:STRING conta_origem:STRING! item_id_viu2:INTEGER item_id_globocorp:INTEGER "
        "motivo_pool:STRING! talentos_json:STRING entrada_utc:TIMESTAMP! mes_entrada:DATE! situacao_atual:STRING! "
        "status_atual:STRING quantidade_entregas:INTEGER! quantidade_retrabalhos:INTEGER! "
        "tempo_orcamento_horas_uteis:FLOAT tempo_ate_primeira_entrega_horas_uteis:FLOAT espera_marca_horas_uteis:FLOAT "
        "standby_horas_uteis:FLOAT resposta_cliente_horas_uteis:FLOAT completo:BOOLEAN! marca:STRING "
        "tipo_input:STRING responsavel:STRING corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_sla_sem_entrada": _fields(
        "projeto_id:STRING! projeto_nome:STRING conta_origem:STRING! item_id_viu2:INTEGER item_id_globocorp:INTEGER "
        "primeiro_status:STRING primeiro_status_utc:TIMESTAMP status_atual:STRING passa_por_entrada_depois:BOOLEAN! "
        "quantidade_passagens:INTEGER! quantidade_entregas:INTEGER! horas_uteis_conhecidas:FLOAT trajeto:STRING! "
        "trajeto_json:STRING! marca:STRING talento:STRING responsavel:STRING corte_utc:TIMESTAMP! versao_regra:STRING!"),
    "monday_dim_talento": _fields(
        "chave_talento:STRING! talento_nome:STRING! variantes_json:STRING! quantidade_variantes:INTEGER! "
        "eh_exclusivo:BOOLEAN! usos_exclusivo:INTEGER! usos_interveniencia:INTEGER! itens_quadro:INTEGER! "
        "projetos_no_sla:INTEGER! projetos_pool:INTEGER! possivel_duplicata_de:STRING corte_utc:TIMESTAMP! "
        "versao_regra:STRING!"),
    "monday_dim_marca": _fields(
        "chave_marca:STRING! marca_nome:STRING! variantes_json:STRING! quantidade_variantes:INTEGER! "
        "itens_quadro:INTEGER! projetos_no_sla:INTEGER! possivel_duplicata_de:STRING corte_utc:TIMESTAMP! "
        "versao_regra:STRING!"),
})

KEYS = {
    "monday_sla_projeto": ("projeto_id",), "monday_sla_ciclo": ("ciclo_id",),
    "monday_sla_passagem": ("interval_id",), "monday_sla_tempo_status": ("projeto_id", "status_nome"),
    "monday_sla_resposta_cliente": ("interval_id",), "monday_sla_em_andamento": ("projeto_id",),
    "monday_sla_referencia_status": ("status_nome",), "monday_sla_gargalo_mensal": ("mes", "status_nome"),
    "monday_sla_kpi_mensal": ("mes",), "monday_sla_qualidade": ("chave",),
    "monday_sla_erro_preenchimento": ("erro_id",), "monday_sla_qualidade_preenchimento": ("mes", "responsavel"),
    "monday_dim_status": ("status_nome",), "monday_dim_calendario": ("data",),
    "monday_sla_projeto_diario": ("projeto_id", "data"),
    "monday_sla_item_duplicado": ("projeto_id",), "monday_sla_standby": ("projeto_id",),
    "monday_sla_projeto_pool": ("projeto_id",), "monday_sla_sem_entrada": ("projeto_id",),
    "monday_dim_talento": ("chave_talento",), "monday_dim_marca": ("chave_marca",),
}
CLUSTERING = {
    "monday_sla_projeto": ["situacao_atual", "marca"], "monday_sla_passagem": ["projeto_id", "status_nome"],
    "monday_sla_ciclo": ["projeto_id"], "monday_sla_projeto_diario": ["projeto_id"],
    "monday_sla_erro_preenchimento": ["tipo_erro", "responsavel"],
}
PARTITION_MONTH = {"monday_sla_projeto_diario": "data"}

ERRORS = {
    "inicio_sem_entrada": ("erro", "Chegou em Aguardando Feedback ou outra etapa sem passar por Entrada"),
    "terminal_no_meio": ("erro", "Encerrado/Declinado seguido de mais trabalho no mesmo item"),
    "status_sem_rotulo": ("erro", "Status vazio no meio da trajetória"),
    "entrega_sem_elaboracao": ("atencao", "Foi de Entrada direto para Aguardando Feedback, sem etapa de elaboração"),
    "entrada_repetida": ("atencao", "Voltou para Entrada no meio da elaboração"),
    "resposta_nao_registrada": ("processo", "Aguardando Feedback encerrado pela automação (~29 dias), sem registro da resposta do cliente"),
    "parado_em_standby": ("atencao", f"Parado em Standby há mais de {STANDBY_STALE_DAYS} dias"),
    "nasceu_de_copia": ("atencao", "Item duplicado de outro orçamento (nasce em Aguardando Feedback ou Encerrado e vai para Entrada)"),
    "duplicado_original_ambiguo": ("atencao", "Item duplicado com mais de um orçamento original possível; vínculo deixado em branco"),
    "talento_nao_informado": ("erro", "Cadastro sem talento: Talentos Exclusivos e Interveniência vazios"),
    "talento_multiplo": ("processo", "Mais de um talento no mesmo item (pool): o certo é um projeto por talento"),
    "talento_ambas_colunas": ("erro", "Talentos diferentes em Talentos Exclusivos e Interveniência"),
    "talento_squad": ("processo", "Squad de talentos (pool): o certo é um projeto por talento"),
    "marca_vazia": ("erro", "Cadastro sem marca"),
    "tipo_input_vazio": ("atencao", "Cadastro sem Tipo de Input"),
    "responsavel_vazio": ("atencao", "Cadastro sem responsável pelo orçamento"),
}


def novo_status(label):
    """Status propostos em 28/09: aprovado, sem retorno do cliente e contraproposta."""
    value = normalize(label)
    if value.startswith("aprovado") or "negócio fechado" in value or "negocio fechado" in value:
        return "aprovado"
    if value.startswith("sem retorno"):
        return "sem_retorno"
    if value.startswith(("contraproposta", "contra proposta", "novo escopo")):
        return "contraproposta"
    return None


def categoria(label):
    value = normalize(label)
    if not value or value == normalize("Sem status"):
        return "desconhecido"
    novo = novo_status(label)
    if novo in ("aprovado", "sem_retorno"):
        return "terminal"
    if novo == "contraproposta":
        return "trabalho"
    if value == FEEDBACK:
        return "entrega"
    if value == STANDBY:
        return "standby"
    if value in BRAND_WAIT:
        return "espera_marca"
    if value in TERMINALS:
        return "terminal"
    if value in WORK or value.startswith(("em elabora", "em revis")):
        return "trabalho"
    return "desconhecido"


def instant(value):
    if value is None or isinstance(value, datetime):
        return value.astimezone(UTC) if value else None
    result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("Modelo v19: timestamp sem fuso")
    return result.astimezone(UTC)


def iso(value):
    return value.astimezone(UTC).isoformat(timespec="microseconds") if value else None


def local_date(value):
    return value.astimezone(ZONE).date()


def month(value):
    day = local_date(value) if isinstance(value, datetime) else value
    return day.replace(day=1).isoformat()


def people_names(raw):
    try:
        people = json.loads(raw) if raw else []
    except ValueError:
        return None
    names = [p.get("nome") for p in people if isinstance(p, dict) and p.get("nome")]
    return " + ".join(names) if names else None


def total(values):
    """Soma que respeita desconhecido: qualquer None torna o total None."""
    values = list(values)
    return None if any(v is None for v in values) else round(sum(values), 3)


def percentile(values, q):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    k = (len(values) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(values) - 1)
    return round(values[lo] + (values[hi] - values[lo]) * (k - lo), 3)


def key(*parts):
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


# ---------------------------------------------------------------- entradas

def from_v18(sla_rows):
    """Passagens de projetos com par ViU2↔Globocorp, já validadas pela v18."""
    passages, attrs = defaultdict(list), {}
    for r in sla_rows:
        pid = r["projeto_id"]
        passages[pid].append({
            "interval_id": r["interval_id"], "status_nome": r["status_nome"], "conta": r["ambiente_origem"],
            "inicio": instant(r["entrada_status_utc"]), "saida": instant(r["saida_status_utc"]),
            "fim": instant(r.get("sla_referencia_ate_utc")), "origem": r.get("sla_origem_duracao") or "indisponivel",
            "horas_uteis": r.get("sla_horas_uteis"), "horas_corridas": r.get("sla_horas_corridas"),
        })
        attrs.setdefault(pid, {
            "projeto_nome": r["projeto_nome"], "item_id_viu2": r["item_id_viu2"],
            "item_id_globocorp": r["item_id_globocorp"],
            "marca": r.get("cadastro_atual_marca") or r.get("marca_nome") or r.get("marca_original"),
            "talento": r.get("talento_nome_atual") or r.get("talento_nome") or r.get("talento_original"),
            "eh_interveniencia": r.get("eh_interveniencia"), "tipo_input": r.get("cadastro_atual_tipo_input"),
            "tipo_projeto": r.get("cadastro_atual_tipo_projeto"),
            "responsavel": people_names(r.get("cadastro_atual_orcamento_json")) or r.get("responsavel_orcamento"),
            "nasceu_de_copia": False,
        })
    for pid in passages:
        attrs[pid]["contas"] = {p["conta"] for p in passages[pid]}
    return passages, attrs


def native_globocorp(new_rows, mapped_items, context_index, calendar, cut):
    """Projetos que nasceram na Globocorp (sem par na ViU2): histórico completo lá (R9)."""
    by_item = defaultdict(list)
    for r in new_rows:
        if int(r["item_id"]) not in mapped_items:
            by_item[int(r["item_id"])].append(r)
    passages, attrs, excluded = {}, {}, {}
    for item, rows in by_item.items():
        rows.sort(key=lambda r: (r["ordem_etapa"], r["interval_id"]))
        pid = str(uuid5(NAMESPACE, f"globocorp-nativo:{item}"))
        context = context_index.get(item) or {}
        name = rows[-1]["projeto_nome"]
        initial = rows[0]["status_nome"] if rows[0]["entrada_status_utc"] is None else None
        reasons = list(motivos_exclusao(name)) + list(motivos_input(context.get("tipo_input")))
        if context:
            reasons += talent_exclusions(context)
        else:
            reasons.append("sem_cadastro_atual")
        pool = sorted(set(reasons) & POOL) if is_pool(reasons) else []
        if reasons and not pool:
            excluded[pid] = {"item_id_globocorp": item, "projeto_nome": name, "motivos": sorted(set(reasons)),
                             "passagens": len(rows)}
            continue
        items = []
        dated = [r for r in rows if r["entrada_status_utc"] is not None]
        for i, r in enumerate(dated):
            start, end = instant(r["entrada_status_utc"]), instant(r["saida_status_utc"])
            origin, reference = "indisponivel", None
            if end is not None and r["qualidade_historico"] == "observed":
                origin, reference = "observada", end
            elif end is None and i == len(dated) - 1 and r.get("intervalo_aberto") and r["qualidade_historico"] == "observed":
                origin, reference = "idade_aberta_no_corte", cut
            hours = calendar.hours(start, reference) if reference else None
            items.append({
                "interval_id": str(uuid5(NAMESPACE, "globocorp:" + r["interval_id"])), "status_nome": r["status_nome"],
                "conta": "globocorp", "inicio": start, "saida": end, "fim": reference, "origem": origin,
                "horas_uteis": round(hours, 3) if hours is not None else None,
                "horas_corridas": round((reference - start).total_seconds() / 3600, 3) if reference else None,
            })
        if not items:
            excluded[pid] = {"item_id_globocorp": item, "projeto_nome": name,
                             "motivos": ["sem_evento_datado"], "passagens": len(rows)}
            continue
        passages[pid] = items
        attrs[pid] = {
            "projeto_nome": name, "item_id_viu2": None, "item_id_globocorp": item, "contas": {"globocorp"},
            "marca": context.get("marca"), "talento": None, "eh_interveniencia": None,
            "tipo_input": context.get("tipo_input"), "tipo_projeto": context.get("tipo_projeto"),
            "responsavel": people_names(context.get("orcamento_json")),
            "nasceu_de_copia": categoria(initial) in ("entrega", "terminal", "trabalho", "espera_marca"),
            "status_copiado": initial,
        }
        if pool:
            attrs[pid]["pool"] = pool
        names = json.loads(context.get("talentos_exclusivos_json") or "[]")
        inter = (context.get("interveniencia") or "").strip()
        attrs[pid]["talentos"] = [n.strip() for n in names if n.strip()] + ([inter] if inter else [])
        attrs[pid]["talento"] = names[0].strip() if names else (inter or None)
        attrs[pid]["eh_interveniencia"] = bool(inter) and not names
    return passages, attrs, excluded


# ---------------------------------------------------------------- núcleo

def build(passages, attrs, *, cut, calendar, excluded=(), board_labels=(), context=(), usage=None):
    cut = instant(cut)
    out = {name: [] for name in CONTRACTS}
    stamp = {"corte_utc": iso(cut), "versao_regra": RULE}
    errors = []
    base_names = {}
    for pid, a in attrs.items():
        base_names.setdefault(_base_name(a["projeto_nome"]), []).append(pid)

    def error(code, pid, a, status=None, at=None, item=None):
        severity, text = ERRORS[code]
        errors.append({
            "erro_id": key(code, pid or item, status, iso(at)), "projeto_id": pid,
            "item_id_globocorp": (a or {}).get("item_id_globocorp", item), "projeto_nome": (a or {}).get("projeto_nome"),
            "tipo_erro": code, "gravidade": severity, "descricao": text, "status_nome": status,
            "ocorrido_em_utc": iso(at), "mes": month(at) if at else None,
            "responsavel": (a or {}).get("responsavel"), "conta_origem": _account(a) if a else "globocorp",
            **stamp})

    for pid in sorted(passages):
        a = attrs[pid]
        rows = sorted(passages[pid], key=lambda p: (p["inicio"], p["interval_id"]))
        known = [i for i, p in enumerate(rows) if categoria(p["status_nome"]) != "desconhecido"]
        first = known[0] if known else None
        if first is None or normalize(rows[first]["status_nome"]) != normalize("Entrada"):
            status = rows[first]["status_nome"] if first is not None else None
            error("inicio_sem_entrada", pid, a, status, rows[first]["inicio"] if first is not None else None)
            out["monday_sla_qualidade"].append(_quality(pid, a, "fora_do_calculo", ["sem_entrada_inicial"], len(rows), stamp))
            _sem_entrada(pid, a, rows, first, out, stamp)
            continue
        if a.get("nasceu_de_copia"):
            error("nasceu_de_copia", pid, a, rows[first]["status_nome"], rows[first]["inicio"])
            _duplicate(pid, a, rows, first, out, stamp, base_names, attrs, error)
            out["monday_sla_qualidade"].append(_quality(pid, a, "fora_do_calculo", ["item_duplicado"], len(rows), stamp))
            continue
        if a.get("pool"):  # R25: medido com as mesmas regras, publicado à parte e fora do SLA oficial
            _pool(pid, a, rows, first, cut, calendar, out, stamp, base_names)
            out["monday_sla_qualidade"].append(_quality(pid, a, "fora_do_escopo", a["pool"], len(rows), stamp))
            continue
        _project(pid, a, rows, first, cut, calendar, out, error, stamp, base_names)

    for pid, info in dict(excluded).items():
        a = {"projeto_nome": info.get("projeto_nome"), "item_id_viu2": info.get("item_id_viu2"),
             "item_id_globocorp": info.get("item_id_globocorp"), "contas": set(info.get("contas", ()))}
        state = ("fora_do_escopo" if not {"sem_entrada_inicial", "sem_evento_datado", "sem_historico_de_status"} & set(info["motivos"])
                 else "fora_do_calculo")
        real_pid = None if str(pid).startswith("item:") else pid  # item do quadro sem projeto montado
        out["monday_sla_qualidade"].append(_quality(real_pid, a, state, info["motivos"], info.get("passagens", 0), stamp))

    for item in context:
        _registration_errors(item, error)
    seen = set()
    for e in errors:  # mesma ocorrência vinda de duas fontes conta uma vez
        if e["erro_id"] not in seen:
            seen.add(e["erro_id"])
            out["monday_sla_erro_preenchimento"].append(e)

    _references(out, cut, stamp)
    _catalogs(out, context, attrs, stamp)
    _open_alerts(out)
    _monthly(out, stamp)
    _fill_quality(out, stamp)
    _dimensions(out, board_labels, cut, calendar, stamp, usage)
    validate(out)
    return out


def _base_name(name):
    text = normalize(name)
    return re.sub(r"\s*[\[(](contra ?proposta|novo escopo[^\])]*|ajuste[^\])]*|nova proposta|cen[aá]rio \d+)[\])]\s*$", "", text).strip()


def _account(a):
    contas = a.get("contas") or set()
    return "viu2+globocorp" if len(contas) > 1 else next(iter(contas), "globocorp")


def _quality(pid, a, state, reasons, count, stamp):
    return {"chave": pid or f"item:{a.get('item_id_globocorp')}", "projeto_id": pid,
            "item_id_viu2": a.get("item_id_viu2"), "item_id_globocorp": a.get("item_id_globocorp"),
            "projeto_nome": a.get("projeto_nome"), "situacao_calculo": state,
            "motivos_json": json.dumps(sorted(set(reasons)), ensure_ascii=False),
            "conta_origem": _account(a) if a.get("contas") else None, "quantidade_passagens": count, **stamp}


def _project(pid, a, rows, first, cut, calendar, out, error, stamp, base_names):
    # D3: terminal seguido de mais trabalho é erro de preenchimento e é ignorado.
    ignored = {}
    for i, p in enumerate(rows):
        cat = categoria(p["status_nome"])
        if i < first:
            ignored[i] = "antes_da_entrada"
        elif cat == "terminal" and i != len(rows) - 1 and any(
                categoria(q["status_nome"]) != "terminal" for q in rows[i + 1:]):
            ignored[i] = "terminal_no_meio"
            error("terminal_no_meio", pid, a, p["status_nome"], p["inicio"])
        elif cat == "desconhecido":
            error("status_sem_rotulo", pid, a, p["status_nome"], p["inicio"])

    cycles, current, deliveries, answers = [], None, [], []
    passage_cycle = {}
    active = [i for i in range(first, len(rows)) if i not in ignored]
    for pos, i in enumerate(active):
        p, cat = rows[i], categoria(rows[i]["status_nome"])
        nxt = rows[active[pos + 1]] if pos + 1 < len(active) else None
        # R4: só a volta ao trabalho abre ciclo; pausa, marca ou status vazio após a entrega não é retrabalho.
        if cat == "trabalho" and current is None:
            current = {"numero": len(cycles) + 1, "tipo": "orcamento" if not cycles else "retrabalho",
                       "inicio": p["inicio"], "fim": None, "situacao": "em_andamento", "itens": [], "entrega": None}
            cycles.append(current)
        if cat == "trabalho" and normalize(p["status_nome"]) == normalize("Entrada") and current and any(
                categoria(q["status_nome"]) == "trabalho" for q in current["itens"]):
            error("entrada_repetida", pid, a, p["status_nome"], p["inicio"])
        if cat == "entrega":
            if current is not None:
                if not any(categoria(q["status_nome"]) == "trabalho" and normalize(q["status_nome"]) != normalize("Entrada")
                           for q in current["itens"]):
                    error("entrega_sem_elaboracao", pid, a, p["status_nome"], p["inicio"])
                current.update(fim=p["inicio"], situacao="entregue", entrega=p["interval_id"])
                current = None
            deliveries.append(p)
            # A resposta do cliente é a próxima ação decisiva; pausa/marca/vazio no caminho não é decisão.
            later = [rows[j] for j in active[pos + 1:]]
            decisive = next((q for q in later if categoria(q["status_nome"]) in ("trabalho", "entrega", "terminal")), None)
            answers.append((p, decisive, nxt))
        elif cat == "terminal":
            if current is not None:
                current.update(fim=p["inicio"], situacao="interrompido")
                current = None
        elif current is not None:
            current["itens"].append(p)
            passage_cycle[p["interval_id"]] = current

    # Ciclos
    project_cycles = []
    for c in cycles:
        items = c["itens"]
        work = [q for q in items if categoria(q["status_nome"]) == "trabalho"]
        unknown = any(categoria(q["status_nome"]) == "desconhecido" for q in items)
        end = c["fim"] or cut
        complete = not unknown and all(q["horas_uteis"] is not None for q in work)
        cid = str(uuid5(NAMESPACE, f"{ID_SEED}/{pid}/{c['numero']}"))
        c["ciclo_id"] = cid
        row = {
            "ciclo_id": cid, "projeto_id": pid, "numero_ciclo": c["numero"], "tipo_ciclo": c["tipo"],
            "inicio_utc": iso(c["inicio"]), "fim_utc": iso(c["fim"]), "situacao": c["situacao"],
            "trabalho_horas_uteis": total(q["horas_uteis"] for q in work) if complete else None,
            "trabalho_horas_corridas": total(q["horas_corridas"] for q in work) if complete else None,
            "espera_marca_horas_uteis": total(q["horas_uteis"] for q in items if categoria(q["status_nome"]) == "espera_marca"),
            "standby_horas_uteis": total(q["horas_uteis"] for q in items if categoria(q["status_nome"]) == "standby"),
            "bruto_horas_uteis": round(calendar.hours(c["inicio"], end), 3) if end >= c["inicio"] else None,
            "passagens_trabalho": len(work), "completo": complete,
            "contem_estimativa": any(q["origem"] == "estimada_migracao" for q in items),
            "interval_id_entrega": c["entrega"], "mes_fim": month(c["fim"]) if c["fim"] else None, **stamp}
        out["monday_sla_ciclo"].append(row)
        project_cycles.append(row)

    # Resposta do cliente
    response_hours = []
    for n, (p, nxt, pause) in enumerate(answers, 1):
        outcome, counts, following = "aguardando", True, None
        days = None
        if nxt is None and pause is not None:
            nxt, outcome, counts = pause, "pausado", False
            following = pause["status_nome"]
            days = (local_date(pause["inicio"]) - local_date(p["inicio"])).days
        elif nxt is not None:
            following = nxt["status_nome"]
            days = (local_date(nxt["inicio"]) - local_date(p["inicio"])).days
            ncat = categoria(following)
            if ncat == "terminal" and novo_status(following) == "aprovado":
                outcome = "decidiu_aprovado"
            elif ncat == "terminal" and novo_status(following) == "sem_retorno":
                outcome, counts = "sem_retorno_cliente", False
            elif ncat == "terminal":
                if normalize(following) == normalize("Encerrado") and days in AUTO_CLOSE_DAYS:
                    outcome, counts = "encerrado_automatico", False
                    error("resposta_nao_registrada", pid, a, p["status_nome"], p["inicio"])
                else:
                    outcome = "decidiu_declinado" if "declinado" in normalize(following) else "decidiu_encerrado"
            elif ncat == "entrega":
                outcome = "nova_entrega_sem_ajuste"
            else:
                outcome = "pediu_ajuste"
        hours = p["horas_uteis"]
        if outcome == "aguardando" and hours is None:
            hours = round(calendar.hours(p["inicio"], cut), 3)
        if counts and outcome != "aguardando":
            response_hours.append(hours)
        out["monday_sla_resposta_cliente"].append({
            "interval_id": p["interval_id"], "projeto_id": pid, "numero_entrega": n, "inicio_utc": iso(p["inicio"]),
            "proxima_acao_utc": iso(nxt["inicio"]) if nxt else None, "desfecho": outcome, "status_seguinte": following,
            "conta_como_resposta": counts, "horas_uteis": hours, "dias_corridos": days,
            "origem_duracao": p["origem"] if outcome != "aguardando" else "idade_aberta_no_corte",
            "mes_inicio": month(p["inicio"]), **stamp})

    # Passagens e tempo por status
    status_groups = defaultdict(list)
    for order, p in enumerate(rows, 1):
        cat = categoria(p["status_nome"])
        cycle = passage_cycle.get(p["interval_id"])
        reason = ignored.get(order - 1)
        out["monday_sla_passagem"].append({
            "interval_id": p["interval_id"], "projeto_id": pid, "ordem": order, "status_nome": p["status_nome"],
            "categoria": cat, "ciclo_id": cycle["ciclo_id"] if cycle else None,
            "conta_no_tempo_orcamento": bool(cycle) and cat == "trabalho", "ignorada": reason is not None,
            "motivo_ignorada": reason, "conta_origem": p["conta"], "inicio_utc": iso(p["inicio"]),
            "saida_observada_utc": iso(p["saida"]), "fim_referencia_utc": iso(p["fim"]),
            "origem_duracao": p["origem"], "horas_uteis": p["horas_uteis"], "horas_corridas": p["horas_corridas"],
            "mes_inicio": month(p["inicio"]), **stamp})
        if reason is None and p["status_nome"]:
            status_groups[p["status_nome"]].append((order, p))
    for status, items in sorted(status_groups.items()):
        visits = sum(1 for k, (order, _) in enumerate(items) if k == 0 or items[k - 1][0] != order - 1)
        out["monday_sla_tempo_status"].append({
            "projeto_id": pid, "status_nome": status, "categoria": categoria(status), "visitas": visits,
            "passagens": len(items), "horas_uteis": total(p["horas_uteis"] for _, p in items),
            "horas_corridas": total(p["horas_corridas"] for _, p in items),
            "completo": all(p["horas_uteis"] is not None for _, p in items),
            "contem_estimativa": any(p["origem"] == "estimada_migracao" for _, p in items), **stamp})

    # Projeto
    delivered = [c for c in project_cycles if c["situacao"] == "entregue"]
    complete = all(c["completo"] for c in delivered)
    last = rows[active[-1]]
    last_cat = categoria(last["status_nome"])
    open_cycle = next((c for c in project_cycles if c["situacao"] == "em_andamento"), None)
    if last_cat == "entrega":
        state = "aguardando_cliente"
    elif last_cat == "terminal":
        answer = out["monday_sla_resposta_cliente"][-1] if deliveries else None
        outcome_state = {"encerrado_automatico": "encerrado_automatico", "decidiu_aprovado": "negocio_fechado",
                         "sem_retorno_cliente": "sem_retorno_cliente"}
        state = ("interrompido" if not deliveries
                 else outcome_state.get(answer["desfecho"], "cliente_decidiu") if answer else "cliente_decidiu")
    elif last_cat == "standby":
        state = "parado_standby"
        if (cut - last["inicio"]).days > STANDBY_STALE_DAYS:
            error("parado_em_standby", pid, a, last["status_nome"], last["inicio"])
    elif last_cat == "espera_marca":
        state = "aguardando_marca"
    elif last_cat == "trabalho":
        state = "em_retrabalho" if deliveries else "em_orcamento"
    else:
        state = "indeterminado"
    first_delivery = deliveries[0]["inicio"] if deliveries else None
    entry = rows[first]["inicio"]
    project = {
        "projeto_id": pid, "projeto_nome": a["projeto_nome"], "conta_origem": _account(a),
        "item_id_viu2": a.get("item_id_viu2"), "item_id_globocorp": a.get("item_id_globocorp"),
        "entrada_utc": iso(entry), "mes_entrada": month(entry), "situacao_atual": state,
        "status_atual": last["status_nome"], "primeira_entrega_utc": iso(first_delivery),
        "ultima_entrega_utc": iso(deliveries[-1]["inicio"]) if deliveries else None,
        "quantidade_entregas": len(deliveries),
        "quantidade_retrabalhos": sum(c["tipo_ciclo"] == "retrabalho" for c in project_cycles),
        "tempo_orcamento_horas_uteis": total(c["trabalho_horas_uteis"] for c in delivered) if delivered and complete else None,
        "tempo_orcamento_horas_corridas": total(c["trabalho_horas_corridas"] for c in delivered) if delivered and complete else None,
        "tempo_ate_primeira_entrega_horas_uteis": delivered[0]["trabalho_horas_uteis"] if delivered else None,
        "bruto_ate_primeira_entrega_horas_uteis": round(calendar.hours(entry, first_delivery), 3) if first_delivery else None,
        "espera_marca_horas_uteis": total(rows[i]["horas_uteis"] for i in active
                                          if categoria(rows[i]["status_nome"]) == "espera_marca"),
        "standby_horas_uteis": total(rows[i]["horas_uteis"] for i in active
                                     if categoria(rows[i]["status_nome"]) == "standby"),
        "resposta_cliente_horas_uteis": total(response_hours) if response_hours else None,
        "completo": complete and all(c["completo"] for c in project_cycles),
        "contem_estimativa": any(p["origem"] == "estimada_migracao" for p in rows),
        "nasceu_de_copia": bool(a.get("nasceu_de_copia")), "projeto_relacionado": None,
        "marca": a.get("marca"), "talento": a.get("talento"), "eh_interveniencia": a.get("eh_interveniencia"),
        "tipo_input": a.get("tipo_input"), "tipo_projeto": a.get("tipo_projeto"), "responsavel": a.get("responsavel"),
        **stamp}
    out["monday_sla_projeto"].append(project)

    if state == "parado_standby":
        previous = next((rows[i]["status_nome"] for i in reversed(active[:-1])
                         if categoria(rows[i]["status_nome"]) != "standby"), None)
        out["monday_sla_standby"].append({
            "projeto_id": pid, "projeto_nome": a["projeto_nome"], "em_standby_desde_utc": iso(last["inicio"]),
            "dias_corridos_parado": (local_date(cut) - local_date(last["inicio"])).days,
            "horas_uteis_parado": round(calendar.hours(last["inicio"], cut), 3), "status_anterior": previous,
            "quantidade_entregas": len(deliveries),
            "acima_do_limite": (cut - last["inicio"]).days > STANDBY_STALE_DAYS,
            "responsavel": a.get("responsavel"), "marca": a.get("marca"), "talento": a.get("talento"), **stamp})
    if state in OPEN_STATES:
        out["monday_sla_em_andamento"].append({
            "projeto_id": pid, "projeto_nome": a["projeto_nome"], "situacao_atual": state,
            "status_atual": last["status_nome"], "no_status_desde_utc": iso(last["inicio"]),
            "horas_uteis_no_status": round(calendar.hours(last["inicio"], cut), 3),
            "numero_ciclo_atual": open_cycle["numero_ciclo"] if open_cycle else None,
            "horas_uteis_desde_entrada": round(calendar.hours(entry, cut), 3),
            "referencia_atencao_horas": None, "referencia_critico_horas": None, "nivel_alerta": "sem_referencia",
            "responsavel": a.get("responsavel"), "marca": a.get("marca"), "talento": a.get("talento"), **stamp})

    # Série diária para ML: até a última entrega/terminal, ou até o corte se aberto.
    # Standby continua na série até o corte (parado não é encerrado), sem somar trabalho.
    still_open = state in OPEN_STATES or state in ("indeterminado", "parado_standby")
    stop = cut if still_open else rows[active[-1]]["inicio"]
    work = [p for p in rows if passage_cycle.get(p["interval_id"]) and categoria(p["status_nome"]) == "trabalho"]
    # O corte é meia-noite local: o último dia da série é o anterior a ele, não um dia vazio.
    day, last_day = local_date(entry), local_date(max(entry, stop - timedelta(microseconds=1) if still_open else stop))
    timeline = [rows[i] for i in active]
    while day <= last_day:
        # Início inclusivo e fim exclusivo: um evento às 00:00 pertence ao dia seguinte.
        next_midnight = datetime.combine(day + timedelta(days=1), time.min, ZONE).astimezone(UTC)
        end_of_day = min(next_midnight, stop)
        current = next((p for p in reversed(timeline) if p["inicio"] < next_midnight), timeline[0])
        accumulated = []
        for p in work:
            if p["inicio"] >= end_of_day:
                continue
            if p["fim"] is None:
                accumulated.append(None)
            else:
                accumulated.append(calendar.hours(p["inicio"], min(p["fim"], end_of_day)))
        out["monday_sla_projeto_diario"].append({
            "projeto_id": pid, "data": day.isoformat(), "status_fim_do_dia": current["status_nome"],
            "categoria": categoria(current["status_nome"]),
            "situacao_no_dia": "aberto" if day < last_day or state in OPEN_STATES else state,
            "entregas_ate_o_dia": sum(1 for p in deliveries if p["inicio"] < next_midnight),
            "tempo_orcamento_acumulado_horas_uteis": total(accumulated) if accumulated else 0.0,
            "horas_uteis_desde_entrada": round(calendar.hours(entry, end_of_day), 3) if end_of_day >= entry else 0.0,
            "eh_dia_util": calendar.hours(datetime.combine(day, time.min, ZONE), datetime.combine(day + timedelta(days=1), time.min, ZONE)) > 0,
            "versao_regra": RULE})
        day += timedelta(days=1)


POOL_FIELDS = ("projeto_id", "projeto_nome", "conta_origem", "item_id_viu2", "item_id_globocorp", "entrada_utc",
               "mes_entrada", "situacao_atual", "status_atual", "quantidade_entregas", "quantidade_retrabalhos",
               "tempo_orcamento_horas_uteis", "tempo_ate_primeira_entrega_horas_uteis", "espera_marca_horas_uteis",
               "standby_horas_uteis", "resposta_cliente_horas_uteis", "completo", "marca", "tipo_input", "responsavel")


def _pool(pid, a, rows, first, cut, calendar, out, stamp, base_names):
    """R25: projeto com squad ou vários talentos. Mesmo cálculo de tempo, sem entrar nas tabelas do SLA oficial."""
    scratch = {name: [] for name in CONTRACTS}
    _project(pid, a, rows, first, cut, calendar, scratch, lambda *args, **kwargs: None, stamp, base_names)
    row = scratch["monday_sla_projeto"][0]
    out["monday_sla_projeto_pool"].append({
        **{k: row[k] for k in POOL_FIELDS}, "motivo_pool": ",".join(a["pool"]),
        "talentos_json": json.dumps(a.get("talentos") or [], ensure_ascii=False), **stamp})


def _sem_entrada(pid, a, rows, first, out, stamp):
    """R1: projeto que não começa por Entrada (nem vazio seguido de Entrada) fica fora; a trajetória fica para avaliação."""
    entrada = normalize("Entrada")
    trajectory = [{"ordem": i, "status": p["status_nome"], "inicio_utc": iso(p["inicio"]), "fim_utc": iso(p["fim"]),
                   "horas_uteis": p["horas_uteis"], "conta": p["conta"]} for i, p in enumerate(rows, 1)]
    known = [p["horas_uteis"] for p in rows if p["horas_uteis"] is not None]
    out["monday_sla_sem_entrada"].append({
        "projeto_id": pid, "projeto_nome": a.get("projeto_nome"), "conta_origem": _account(a),
        "item_id_viu2": a.get("item_id_viu2"), "item_id_globocorp": a.get("item_id_globocorp"),
        "primeiro_status": rows[first]["status_nome"] if first is not None else None,
        "primeiro_status_utc": iso(rows[first]["inicio"]) if first is not None else None,
        "status_atual": rows[-1]["status_nome"],
        "passa_por_entrada_depois": any(normalize(p["status_nome"]) == entrada for p in rows),
        "quantidade_passagens": len(rows),
        "quantidade_entregas": sum(1 for p in rows if categoria(p["status_nome"]) == "entrega"),
        "horas_uteis_conhecidas": total(known) if known else None,
        "trajeto": " → ".join(p["status_nome"] or "(vazio)" for p in rows),
        "trajeto_json": json.dumps(trajectory, ensure_ascii=False),
        "marca": a.get("marca"), "talento": a.get("talento"), "responsavel": a.get("responsavel"), **stamp})


def _similar(key, usage):
    """Grafia provavelmente igual a outra mais usada: nome curto contido no longo ("jonas" x "jonas sulzbach")
    ou erro de digitação ("jonas sulbach" x "jonas sulzbach"). Aponta sempre do menos usado para o mais usado."""
    from difflib import SequenceMatcher
    best = None
    for other, uses in usage.items():
        if other == key or (uses, other) <= (usage[key], key):
            continue
        a, b = key.split(), other.split()
        prefix = len(a) < len(b) and b[:len(a)] == a
        close = min(len(key), len(other)) >= 5 and SequenceMatcher(None, key, other).ratio() >= 0.9
        if (prefix or close) and (best is None or uses > usage[best]):
            best = other
    return best


def _catalog_key(text):
    import unicodedata
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return " ".join(re.sub(r"[^0-9a-z]+", " ", text).split())  # "Coca-Cola" e "coca cola" viram a mesma chave


def _catalogs(out, context, attrs, stamp):
    """Catálogo de talentos e de marcas do quadro atual: grafias, uso e possíveis duplicatas (base para correção)."""
    in_sla = {r["item_id_globocorp"] for r in out["monday_sla_projeto"]}
    in_pool = {r["item_id_globocorp"] for r in out["monday_sla_projeto_pool"]}
    talents, brands = {}, {}
    for item in context:
        item_id = int(item["item_id"])
        names = [(n.strip(), True) for n in json.loads(item.get("talentos_exclusivos_json") or "[]") if n and n.strip()]
        inter = (item.get("interveniencia") or "").strip()
        if inter:
            names += [(n.strip(), False) for n in re.split(r"[,;\n\r+]|\s[&/]\s", inter) if n.strip()]
        for name, exclusive in names:
            k = _catalog_key(name)
            if not k or re.search(r"\bsquad\b", k):
                continue
            t = talents.setdefault(k, {"variantes": Counter(), "excl": 0, "inter": 0, "itens": set()})
            t["variantes"][name] += 1
            t["excl" if exclusive else "inter"] += 1
            t["itens"].add(item_id)
        brand = (item.get("marca") or "").strip()
        if brand:
            b = brands.setdefault(_catalog_key(brand), {"variantes": Counter(), "itens": set()})
            b["variantes"][brand] += 1
            b["itens"].add(item_id)
    keys = sorted(talents)
    usage = {k: len(talents[k]["itens"]) for k in keys}
    for k in keys:
        t = talents[k]
        out["monday_dim_talento"].append({
            "chave_talento": k, "talento_nome": t["variantes"].most_common(1)[0][0],
            "variantes_json": json.dumps(dict(t["variantes"].most_common()), ensure_ascii=False),
            "quantidade_variantes": len(t["variantes"]), "eh_exclusivo": t["excl"] > 0,
            "usos_exclusivo": t["excl"], "usos_interveniencia": t["inter"], "itens_quadro": len(t["itens"]),
            "projetos_no_sla": len(t["itens"] & in_sla), "projetos_pool": len(t["itens"] & in_pool),
            "possivel_duplicata_de": _similar(k, usage), **stamp})
    keys = sorted(brands)
    usage = {k: len(brands[k]["itens"]) for k in keys}
    for k in keys:
        b = brands[k]
        out["monday_dim_marca"].append({
            "chave_marca": k, "marca_nome": b["variantes"].most_common(1)[0][0],
            "variantes_json": json.dumps(dict(b["variantes"].most_common()), ensure_ascii=False),
            "quantidade_variantes": len(b["variantes"]), "itens_quadro": len(b["itens"]),
            "projetos_no_sla": len(b["itens"] & in_sla), "possivel_duplicata_de": _similar(k, usage), **stamp})


def _duplicate(pid, a, rows, first, out, stamp, base_names, attrs, error):
    """D2: item copiado de outro orçamento fica fora do SLA, mas guardado para estudo."""
    # Vínculo só com um único original possível (que não seja outra cópia); nome igual não prova qual é.
    others = [o for o in base_names.get(_base_name(a["projeto_nome"]), [])
              if o != pid and not attrs[o].get("nasceu_de_copia")]
    related = others[0] if len(others) == 1 else None
    if len(others) > 1:
        error("duplicado_original_ambiguo", pid, a, rows[first]["status_nome"], rows[first]["inicio"])
    valid = rows[first:]
    deliveries = [p for p in valid if categoria(p["status_nome"]) == "entrega"]
    work = [p["horas_uteis"] for p in valid if categoria(p["status_nome"]) == "trabalho"]
    out["monday_sla_item_duplicado"].append({
        "projeto_id": pid, "item_id_globocorp": a.get("item_id_globocorp"), "projeto_nome": a["projeto_nome"],
        "status_copiado": a.get("status_copiado"), "entrada_utc": iso(rows[first]["inicio"]),
        "mes_entrada": month(rows[first]["inicio"]), "status_atual": rows[-1]["status_nome"],
        "quantidade_entregas": len(deliveries), "primeira_entrega_utc": iso(deliveries[0]["inicio"]) if deliveries else None,
        "trabalho_horas_uteis": total(work) if work else None,
        "trajeto": " → ".join(p["status_nome"] or "(vazio)" for p in rows),
        "projeto_relacionado": related, "projeto_relacionado_nome": attrs[related]["projeto_nome"] if related else None,
        "responsavel": a.get("responsavel"), "marca": a.get("marca"), **stamp})


def _registration_errors(item, error):
    a = {"projeto_nome": item.get("item_nome"), "item_id_globocorp": item.get("item_id"), "contas": {"globocorp"},
         "responsavel": people_names(item.get("orcamento_json"))}
    at = instant(item.get("capturado_em"))
    for code in talent_exclusions(item):
        error(code, None, a, item.get("status_nome"), at, item.get("item_id"))
    if not (item.get("marca") or "").strip():
        error("marca_vazia", None, a, item.get("status_nome"), at, item.get("item_id"))
    if not (item.get("tipo_input") or "").strip():
        error("tipo_input_vazio", None, a, item.get("status_nome"), at, item.get("item_id"))
    if not a["responsavel"]:
        error("responsavel_vazio", None, a, item.get("status_nome"), at, item.get("item_id"))


def _references(out, cut, stamp):
    """SLA de referência por status: P80 = atenção, P90 = crítico, 12 meses observados."""
    start = cut - timedelta(days=365)
    samples = defaultdict(list)
    for p in out["monday_sla_passagem"]:
        if (not p["ignorada"] and p["origem_duracao"] == "observada" and p["horas_uteis"] is not None
                and p["categoria"] in ("trabalho", "espera_marca") and instant(p["inicio_utc"]) >= start):
            samples[p["status_nome"]].append(p["horas_uteis"])
    # Aguardando Feedback: só respostas reais. O encerramento automático (29 dias) mediria a automação.
    for r in out["monday_sla_resposta_cliente"]:
        if (r["conta_como_resposta"] and r["desfecho"] != "aguardando" and r["horas_uteis"] is not None
                and r["origem_duracao"] == "observada" and instant(r["inicio_utc"]) >= start):
            samples["Aguardando Feedback"].append(r["horas_uteis"])
    for status, values in sorted(samples.items()):
        enough = len(values) >= REFERENCE_MIN_SAMPLES
        out["monday_sla_referencia_status"].append({
            "status_nome": status, "categoria": categoria(status), "passagens_observadas": len(values),
            "p50_horas_uteis": percentile(values, .5) if enough else None,
            "p80_horas_uteis": percentile(values, .8) if enough else None,
            "p90_horas_uteis": percentile(values, .9) if enough else None,
            "referencia_atencao_horas": percentile(values, .8) if enough else None,
            "referencia_critico_horas": percentile(values, .9) if enough else None,
            "janela_inicio": local_date(start).isoformat(), **stamp})


def _open_alerts(out):
    refs = {r["status_nome"]: r for r in out["monday_sla_referencia_status"]}
    for row in out["monday_sla_em_andamento"]:
        ref = refs.get(row["status_atual"])
        if not ref or ref["referencia_atencao_horas"] is None:
            continue
        row["referencia_atencao_horas"] = ref["referencia_atencao_horas"]
        row["referencia_critico_horas"] = ref["referencia_critico_horas"]
        hours = row["horas_uteis_no_status"]
        row["nivel_alerta"] = ("critico" if hours > ref["referencia_critico_horas"]
                               else "atencao" if hours > ref["referencia_atencao_horas"] else "ok")


def _monthly(out, stamp):
    by_status = defaultdict(list)
    for p in out["monday_sla_passagem"]:
        if not p["ignorada"] and p["status_nome"] and p["categoria"] != "terminal":
            by_status[(p["mes_inicio"], p["status_nome"])].append(p)
    for (mes, status), items in sorted(by_status.items()):
        hours = [p["horas_uteis"] for p in items if p["horas_uteis"] is not None]
        out["monday_sla_gargalo_mensal"].append({
            "mes": mes, "status_nome": status, "categoria": categoria(status), "passagens": len(items),
            "projetos": len({p["projeto_id"] for p in items}),
            "horas_uteis_total": round(sum(hours), 3) if hours else None,
            "horas_uteis_p50": percentile(hours, .5), "horas_uteis_p80": percentile(hours, .8),
            "passagens_sem_duracao": len(items) - len(hours), **stamp})
    months = defaultdict(lambda: defaultdict(list))
    for p in out["monday_sla_projeto"]:
        months[p["mes_entrada"]]["iniciados"].append(p)
        if p["primeira_entrega_utc"]:
            months[month(instant(p["primeira_entrega_utc"]))]["primeira"].append(p)
    for r in out["monday_sla_resposta_cliente"]:
        months[r["mes_inicio"]]["entregas"].append(r)
        if r["proxima_acao_utc"]:
            months[month(instant(r["proxima_acao_utc"]))]["respostas"].append(r)
    for e in out["monday_sla_erro_preenchimento"]:
        if e["mes"] and e["projeto_id"]:  # erros de trajetória; cadastro é foto do dia
            months[e["mes"]]["erros"].append(e)
    for mes, g in sorted(months.items()):
        first = g["primeira"]
        with_time = [p["tempo_ate_primeira_entrega_horas_uteis"] for p in first]
        adjustments = [r for r in g["respostas"] if r["desfecho"] == "pediu_ajuste"]
        out["monday_sla_kpi_mensal"].append({
            "mes": mes, "projetos_iniciados": len(g["iniciados"]), "entregas": len(g["entregas"]),
            "projetos_primeira_entrega": len(first),
            "tempo_orcamento_p50_horas_uteis": percentile(with_time, .5),
            "tempo_orcamento_p80_horas_uteis": percentile(with_time, .8),
            "pct_projetos_com_retrabalho": round(100 * sum(p["quantidade_retrabalhos"] > 0 for p in first) / len(first), 1) if first else None,
            "pedidos_de_ajuste": len(adjustments),
            "resposta_ajuste_p50_horas_uteis": percentile([r["horas_uteis"] for r in adjustments], .5),
            "encerrados_automaticos": sum(r["desfecho"] == "encerrado_automatico" for r in g["respostas"]),
            "decisoes_registradas": sum(r["desfecho"].startswith("decidiu") for r in g["respostas"]),
            "erros_preenchimento": len(g["erros"]), **stamp})


def _fill_quality(out, stamp):
    started = defaultdict(set)
    for p in out["monday_sla_projeto"]:
        started[(p["mes_entrada"], p["responsavel"] or "(não informado)")].add(p["projeto_id"])
    errors = defaultdict(list)
    for e in out["monday_sla_erro_preenchimento"]:
        if e["mes"] and e["projeto_id"]:
            errors[(e["mes"], e["responsavel"] or "(não informado)")].append(e)
    for key_ in sorted(set(started) | set(errors)):
        es = errors[key_]
        affected = {e["projeto_id"] for e in es}
        n = len(started[key_])
        types = defaultdict(int)
        for e in es:
            types[e["tipo_erro"]] += 1
        out["monday_sla_qualidade_preenchimento"].append({
            "mes": key_[0], "responsavel": key_[1], "projetos_iniciados": n,
            "projetos_com_erro": len(affected & started[key_]) if n else len(affected),
            "pct_projetos_sem_erro": round(100 * (n - len(affected & started[key_])) / n, 1) if n else None,
            "erros": len(es), "erros_graves": sum(e["gravidade"] == "erro" for e in es),
            "tipos_json": json.dumps(dict(sorted(types.items())), ensure_ascii=False), **stamp})


def status_usage(rows):
    """Quantas vezes cada status foi usado, em qualquer projeto (inclusive fora do cálculo)."""
    usage = {}
    for r in rows:
        name, start = r.get("status_nome"), instant(r.get("entrada_status_utc"))
        if not name or start is None:
            continue
        u = usage.setdefault(name, {"passagens": 0, "itens": set(), "datas": []})
        u["passagens"] += 1
        u["itens"].add((r.get("board_id"), r.get("item_id")))
        u["datas"].append(start)
    return usage


def _dimensions(out, board_labels, cut, calendar, stamp, usage=None):
    if usage is None:  # sem fontes brutas: conta as passagens do próprio modelo
        usage = status_usage({"status_nome": p["status_nome"], "entrada_status_utc": p["inicio_utc"],
                              "item_id": p["projeto_id"]} for p in out["monday_sla_passagem"])
    start = cut - timedelta(days=365)
    year = local_date(cut - timedelta(microseconds=1)).year
    labels = {normalize(v) for v in board_labels}
    names = set(usage) | {p["status_nome"] for p in out["monday_sla_passagem"] if p["status_nome"]} | {
        v for v in board_labels if v and v.strip()}
    for name in sorted(names):
        cat = categoria(name)
        out["monday_dim_status"].append({
            "status_nome": name, "categoria": cat, "conta_no_tempo_orcamento": cat == "trabalho",
            "eh_entrega": cat == "entrega", "eh_terminal": cat == "terminal",
            "etapa": 1 if normalize(name) == normalize("Entrada") else STAGE.get(cat) if cat != "trabalho"
            else 3 if normalize(name).startswith("em revis") else 2,
            "no_quadro_atual": normalize(name) in labels,
            "passagens_total": usage[name]["passagens"] if name in usage else 0,
            "itens_total": len(usage[name]["itens"]) if name in usage else 0,
            "passagens_12_meses": sum(d >= start for d in usage[name]["datas"]) if name in usage else 0,
            "passagens_ano_atual": sum(local_date(d).year == year for d in usage[name]["datas"]) if name in usage else 0,
            "primeiro_uso_utc": iso(min(usage[name]["datas"])) if name in usage else None,
            "ultimo_uso_utc": iso(max(usage[name]["datas"])) if name in usage else None,
            "versao_regra": RULE})
    starts = [instant(p["inicio_utc"]) for p in out["monday_sla_passagem"]]
    if starts:
        day, last = local_date(min(starts)), local_date(cut)
        while day <= last:
            midnight = datetime.combine(day, time.min, ZONE)
            hours = calendar.hours(midnight, midnight + timedelta(days=1))
            holiday = calendar.holiday_name(day)
            out["monday_dim_calendario"].append({
                "data": day.isoformat(), "ano": day.year, "mes": day.month, "trimestre": (day.month - 1) // 3 + 1,
                "semana_iso": f"{day.isocalendar()[0]}-W{day.isocalendar()[1]:02d}", "dia_semana": day.isoweekday(),
                "eh_dia_util": hours > 0, "eh_feriado": holiday is not None, "nome_feriado": holiday,
                "horas_uteis_dia": round(hours, 3), "versao_regra": RULE})
            day += timedelta(days=1)


# ---------------------------------------------------------------- validação

def validate(out):
    """Contrato de cada tabela e relacionamentos entre elas; falha em vez de publicar errado."""
    for name, rows in out.items():
        fields = CONTRACTS[name]
        seen = set()
        for r in rows:
            if set(r) != set(fields):
                raise ValueError(f"Modelo v19: schema divergente em {name}")
            for field, (kind, required) in fields.items():
                value = r[field]
                if value is None:
                    if required:
                        raise ValueError(f"Modelo v19: {name}.{field} obrigatório nulo")
                    continue
                if kind == INT and type(value) is not int:
                    raise ValueError(f"Modelo v19: {name}.{field} inteiro inválido")
                if kind == FLT and (type(value) not in (int, float) or value != value):
                    raise ValueError(f"Modelo v19: {name}.{field} número inválido")
                if kind == BOOL and type(value) is not bool:
                    raise ValueError(f"Modelo v19: {name}.{field} booleano inválido")
                if kind in (STR, TS, DAY) and not isinstance(value, str):
                    raise ValueError(f"Modelo v19: {name}.{field} texto/data inválido")
                if kind == DAY:
                    date.fromisoformat(value)
            k = tuple(r[c] for c in KEYS[name])
            if k in seen:
                raise ValueError(f"Modelo v19: chave duplicada em {name}")
            seen.add(k)
    projects = {p["projeto_id"] for p in out["monday_sla_projeto"]}
    cycles = {c["ciclo_id"] for c in out["monday_sla_ciclo"]}
    for name in ("monday_sla_ciclo", "monday_sla_passagem", "monday_sla_tempo_status",
                 "monday_sla_resposta_cliente", "monday_sla_em_andamento", "monday_sla_projeto_diario"):
        if any(r["projeto_id"] not in projects for r in out[name]):
            raise ValueError(f"Modelo v19: {name} com projeto órfão")
    if any(p["ciclo_id"] is not None and p["ciclo_id"] not in cycles for p in out["monday_sla_passagem"]):
        raise ValueError("Modelo v19: passagem com ciclo órfão")
    by_project = defaultdict(list)
    for c in out["monday_sla_ciclo"]:
        by_project[c["projeto_id"]].append(c)
    for p in out["monday_sla_projeto"]:
        delivered = [c for c in by_project[p["projeto_id"]] if c["situacao"] == "entregue"]
        if p["tempo_orcamento_horas_uteis"] is not None and abs(
                p["tempo_orcamento_horas_uteis"] - sum(c["trabalho_horas_uteis"] for c in delivered)) > 0.01:
            raise ValueError("Modelo v19: tempo do projeto diverge da soma dos ciclos")
        if p["quantidade_entregas"] < len(delivered):
            raise ValueError("Modelo v19: entregas menores que ciclos entregues")
    if any(r["projeto_id"] not in projects for r in out["monday_sla_standby"]):
        raise ValueError("Modelo v19: standby com projeto órfão")
    for name in ("monday_sla_projeto_pool", "monday_sla_sem_entrada"):
        if projects & {r["projeto_id"] for r in out[name]}:
            raise ValueError(f"Modelo v19: {name} misturado ao SLA oficial")
    if projects & {r["projeto_id"] for r in out["monday_sla_item_duplicado"]}:
        raise ValueError("Modelo v19: item duplicado dentro do cálculo")
    included = projects & {q["projeto_id"] for q in out["monday_sla_qualidade"] if q["situacao_calculo"] != "incluido_com_ressalva"}
    if included:
        raise ValueError("Modelo v19: projeto ao mesmo tempo no cálculo e fora dele")
    _validate_consistency(out, by_project)
    return out


def _validate_consistency(out, by_project):
    """Regras de coerência além do esquema: um corte só, durações não negativas e ciclos batendo com o projeto."""
    cuts = {r["corte_utc"] for rows in out.values() for r in rows if "corte_utc" in r}
    if len(cuts) > 1:
        raise ValueError("Modelo v19: mais de um corte na mesma publicação")
    for name, rows in out.items():
        measures = [f for f, (kind, _) in CONTRACTS[name].items()
                    if kind in (INT, FLT) and ("horas" in f or f.startswith("dias_"))]
        for r in rows:
            for f in measures:
                if r[f] is not None and r[f] < -0.001:
                    raise ValueError(f"Modelo v19: {name}.{f} negativo")
    for c in out["monday_sla_ciclo"]:
        if c["fim_utc"] is not None and instant(c["fim_utc"]) < instant(c["inicio_utc"]):
            raise ValueError("Modelo v19: ciclo termina antes de começar")
    for p in out["monday_sla_passagem"]:
        if p["fim_referencia_utc"] is not None and instant(p["fim_referencia_utc"]) < instant(p["inicio_utc"]):
            raise ValueError("Modelo v19: passagem termina antes de começar")
    for p in out["monday_sla_projeto"]:
        rework = sum(c["tipo_ciclo"] == "retrabalho" for c in by_project[p["projeto_id"]])
        if p["quantidade_retrabalhos"] != rework:
            raise ValueError("Modelo v19: retrabalhos do projeto divergem dos ciclos")


def board_status_labels(board_raw):
    """Rótulos configurados na coluna de status do quadro atual (para achar status sem uso)."""
    column = next((c for c in board_raw.get("columns", []) if c.get("id") == "status_19"), None)
    if not column:
        return []
    return sorted(v for v in json.loads(column.get("settings_str") or "{}").get("labels", {}).values() if v)


def from_pipeline(sla_rows, quality_rows, consolidation_report, new_rows, mapping, context, *, cut, calendar,
                  board_labels=(), old_rows=()):
    """Adapta as saídas da execução diária (v18 + fonte Globocorp) às entradas do modelo v19."""
    passages, attrs = from_v18(sla_rows)
    for pid, reasons in (consolidation_report.get("pool_projects") or {}).items():
        if pid in attrs:
            attrs[pid]["pool"] = sorted(reasons)
    mapped = {int(p["globocorp_item_id"]) for p in mapping["rows"]}
    context_index = {int(c["item_id"]): c for c in context}
    native, native_attrs, excluded = native_globocorp(new_rows, mapped, context_index, calendar, instant(cut))
    passages.update(native)
    attrs.update(native_attrs)
    for q in quality_rows:
        if q["projeto_id"] not in passages:
            excluded[q["projeto_id"]] = {
                "projeto_nome": q["projeto_nome"], "item_id_viu2": q["item_id_viu2"],
                "item_id_globocorp": q["item_id_globocorp"], "passagens": q["quantidade_passagens"],
                "motivos": json.loads(q["motivos_json"])}
    pairs = {p["projeto_id"]: p for p in mapping["rows"]}
    for pid, reasons in (consolidation_report.get("excluded_projects_detail") or {}).items():
        if pid not in passages and pid not in excluded:
            pair = pairs.get(pid, {})
            excluded[pid] = {"projeto_nome": None, "item_id_viu2": _int(pair.get("viu2_item_id")),
                             "item_id_globocorp": _int(pair.get("globocorp_item_id")), "passagens": 0,
                             "motivos": sorted(reasons)}
    # R15: todo item do quadro atual aparece em algum lugar. Itens sem nenhuma mudança de status na
    # Globocorp e sem vínculo com a ViU2 (cópias da migração) vão para a qualidade com o motivo.
    seen = ({_int(a.get("item_id_globocorp")) for a in attrs.values()}
            | {_int(e.get("item_id_globocorp")) for e in excluded.values()})
    for item_id, c in context_index.items():
        if item_id not in seen:
            reasons = sorted(set(motivos_exclusao(c.get("item_nome"))) | set(motivos_input(c.get("tipo_input")))
                             | set(talent_exclusions(c)))
            excluded[f"item:{item_id}"] = {"projeto_nome": c.get("item_nome"), "item_id_viu2": None,
                                           "item_id_globocorp": item_id, "passagens": 0,
                                           "motivos": reasons or ["sem_historico_de_status"]}
    usage = status_usage([*old_rows, *new_rows]) if old_rows else None
    return build(passages, attrs, cut=cut, calendar=calendar, excluded=excluded,
                 board_labels=board_labels, context=context, usage=usage)


def _int(value):
    return int(value) if value not in (None, "") else None
