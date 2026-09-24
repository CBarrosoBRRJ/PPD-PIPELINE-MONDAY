"""Conservative, source-preserving trajectory contract; no inferred migration SLA.

Only selected pairs represented in the current published Gold participate.
Unknown-time source references are excluded, not chronological passages.
No source metrics or current attributes are propagated across environments.
"""

import json
import math
import unicodedata
from collections import Counter, defaultdict
from datetime import UTC, datetime
from uuid import UUID, uuid5

from monday_comum.escopo_sla import VERSION as TITLE_SCOPE_VERSION
from monday_comum.escopo_sla import motivos_exclusao, motivos_input
from sls_orcamento_ppd.rules.business_time import BusinessCalendar

from monday_sla_orcamento.analysis_duration import FIELDS as ANALYSIS_FIELDS
from monday_sla_orcamento.analysis_duration import project as analysis_project
from monday_sla_orcamento.consumo import FIELDS as CONSUMPTION_FIELDS
from monday_sla_orcamento.consumo import project as consumption_project
from monday_sla_orcamento.current_context import FIELDS as CONTEXT_FIELDS
from monday_sla_orcamento.current_context import project as context_project
from monday_sla_orcamento.estimates import FIELDS as ESTIMATE_FIELDS
from monday_sla_orcamento.estimates import project as estimate_project
from monday_sla_orcamento.kpi_etapa import decision
from monday_sla_orcamento.pricing import FIELDS as PRICING_FIELDS
from monday_sla_orcamento.pricing import project as pricing_project
from monday_sla_orcamento.talent_context import FIELDS as TALENT_FIELDS
from monday_sla_orcamento.talent_context import project as talent_project
from monday_sla_orcamento.trajectory import FIELDS as TRAJECTORY_FIELDS
from monday_sla_orcamento.trajectory import audit as audit_trajectory
from monday_sla_orcamento.trajectory import project as trajectory_project

LEGACY_VERSION = "sla-consolidado-evidencias-v2"
STAGE_VERSION = "sla-consolidado-etapa-v3"
CONSUMPTION_VERSION = "sla-consolidado-consumo-v4"
TRAJECTORY_VERSION = "sla-consolidado-trajetoria-v5"
ESTIMATE_VERSION = "sla-consolidado-estimativas-v6"
ANALYSIS_VERSION = "sla-consolidado-analise-v7"
PRICING_VERSION = "sla-consolidado-precificacao-v8"
VERSION = "sla-consolidado-talentos-v9"
TERMINAL_LABELS = ("Encerrado", "Declinado pelo Mercado", "Declinado Internamente")
NAMESPACE = UUID("07530d27-26df-4c5f-a2a1-092eb8ef04cf")
SCOPES = {"viu2": ("5890468", 18393336134), "globocorp": ("21453629", 18429499488)}
BASE_FIELDS = {
    "ordem_etapa": ("INTEGER", False), "projeto_nome": ("STRING", False),
    "status_nome": ("STRING", False), "entrada_status_local": ("DATETIME", False),
    "saida_status_local": ("DATETIME", False), "duracao_horas": ("FLOAT", False),
    "duracao_horas_uteis": ("FLOAT", False), "marca_nome": ("STRING", False),
    "talento_nome": ("STRING", False), "responsavel_orcamento": ("STRING", False),
    "marca_original": ("STRING", False), "talento_original": ("STRING", False),
    "eh_retorno": ("BOOLEAN", False), "retorno_observado_origem": ("BOOLEAN", True),
    "projeto_id": ("STRING", True), "item_id": ("INTEGER", True), "board_id": ("INTEGER", True),
    "ambiente_origem": ("STRING", True), "conta_origem": ("STRING", True),
    "interval_id": ("STRING", True), "interval_id_origem": ("STRING", True),
    "item_id_viu2": ("INTEGER", True), "item_id_globocorp": ("INTEGER", True),
    "ordem_origem": ("INTEGER", True), "status_index": ("STRING", True),
    "tipo_registro": ("STRING", True), "qualidade_historico_origem": ("STRING", True),
    "qualidade_identidade": ("STRING", True), "continuidade_validada": ("BOOLEAN", True),
    "elegivel_comparacao": ("BOOLEAN", True), "validacao_negocio": ("STRING", True),
    "entrada_status_utc": ("TIMESTAMP", False), "saida_status_utc": ("TIMESTAMP", False),
    "corte_globocorp_utc": ("TIMESTAMP", True), "cadastro_referencia_utc": ("TIMESTAMP", False),
    "versao_contrato": ("STRING", True), "versao_calendario_origem": ("STRING", True),
    "pendencias_json": ("STRING", True), "registro_origem_json": ("STRING", True),
    "status_terminal": ("BOOLEAN", False), "finalizacao_observada_utc": ("TIMESTAMP", False),
    "situacao_sla_registro": ("STRING", True), "ciclo_observado_origem": ("INTEGER", True),
    "reabertura_comprovada_origem": ("BOOLEAN", True),
    "tempo_ciclo_observado_horas": ("FLOAT", False),
}


PRICING_SCHEMA = {**BASE_FIELDS, **CONSUMPTION_FIELDS, **TRAJECTORY_FIELDS, **ESTIMATE_FIELDS, **ANALYSIS_FIELDS, **PRICING_FIELDS, **CONTEXT_FIELDS}
FIELDS = {**PRICING_SCHEMA, **TALENT_FIELDS}


def fields_for(version):
    if version in (LEGACY_VERSION, STAGE_VERSION):
        return BASE_FIELDS
    if version == CONSUMPTION_VERSION:
        return {**BASE_FIELDS, **CONSUMPTION_FIELDS}
    if version == TRAJECTORY_VERSION:
        return {**BASE_FIELDS, **CONSUMPTION_FIELDS, **TRAJECTORY_FIELDS}
    if version == ESTIMATE_VERSION:
        return {**BASE_FIELDS, **CONSUMPTION_FIELDS, **TRAJECTORY_FIELDS, **ESTIMATE_FIELDS}
    if version == ANALYSIS_VERSION:
        return {**BASE_FIELDS, **CONSUMPTION_FIELDS, **TRAJECTORY_FIELDS, **ESTIMATE_FIELDS, **ANALYSIS_FIELDS}
    if version == PRICING_VERSION:
        return PRICING_SCHEMA
    if version == VERSION:
        return FIELDS
    raise ValueError("Consolidacao: contrato desconhecido")


def schema(version=VERSION):
    return [{"name": k, "type": t, "mode": "REQUIRED" if required else "NULLABLE"}
            for k, (t, required) in fields_for(version).items()]


def timestamp(value):
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.utcoffset() is None:
        raise ValueError("Consolidacao: timestamp sem fuso")
    return parsed.astimezone(UTC)


def normalized_label(value):
    return " ".join(unicodedata.normalize("NFC", value or "").casefold().split())


def annotate_closures(ordered, terminal_labels):
    """Terminal entry closes SLA. No duration across gaps/account boundaries.

Cycle totals are populated on the first terminal row only, and only for a fully
connected source-local chain starting at an observed Entrada. They are not a
complete cross-account/project total. Subsequent terminal rows never extend it.
"""
    terminal_set = {normalized_label(label) for label in terminal_labels}
    states = {}
    for row in ordered:
        env = row["ambiente_origem"]
        state = states.setdefault(env, {"previous": None, "cycle": 1, "start": None, "closed": False})
        previous = state["previous"]
        label = normalized_label(row["status_nome"])
        terminal = label in terminal_set if label else None
        connected = bool(previous and previous["saida_status_utc"] and
                         timestamp(previous["saida_status_utc"]) == timestamp(row["entrada_status_utc"]) and
                         "sobreposicao_temporal_duracao_bloqueada" not in previous["pendencias_json"] and
                         "sobreposicao_temporal_duracao_bloqueada" not in row["pendencias_json"])
        reopening = bool(connected and previous["status_terminal"] is True and terminal is False)
        issues = json.loads(row["pendencias_json"])
        if not connected:
            state["start"] = None
        if reopening:
            state["cycle"] += 1
            state["closed"] = False
            state["start"] = None
        elif state["closed"] and terminal is False:
            issues.append("possivel_reabertura_sem_continuidade_comprovada")
            state["start"] = None
        if label == "entrada" and state["start"] is None and not state["closed"]:
            state["start"] = row["entrada_status_utc"]
        if terminal is None:
            state["start"] = None
            issues.append("classificacao_terminal_desconhecida")
        total = None
        if terminal:
            if state["start"] is not None and not state["closed"]:
                total = round((timestamp(row["entrada_status_utc"]) - timestamp(state["start"])).total_seconds() / 3600, 3)
            state["closed"] = True
            row["duracao_horas"] = row["duracao_horas_uteis"] = None
            issues = [i for i in issues if i != "duracao_fechada_indisponivel"]
            situation = "sla_encerrado_na_entrada_terminal"
        elif terminal is None:
            situation = "status_sem_classificacao"
        elif row["saida_status_utc"] is not None:
            situation = "passagem_com_saida_observada"
        else:
            situation = "sem_saida_observada_nao_comprova_abandono"
        row.update(status_terminal=terminal,
                   finalizacao_observada_utc=row["entrada_status_utc"] if terminal else None,
                   situacao_sla_registro=situation, ciclo_observado_origem=state["cycle"],
                   reabertura_comprovada_origem=reopening, tempo_ciclo_observado_horas=total,
                   pendencias_json=json.dumps(sorted(set(issues))))
        state["previous"] = row


def build(old_rows, new_rows, mapping, *, terminal_labels=TERMINAL_LABELS, old_inputs=None, current_context=None):
    require_old_context = old_inputs is not None
    old_inputs = old_inputs or {}
    if mapping["version"] != "selected-identity-v1":
        raise ValueError("Consolidacao: mapa incompativel")
    indices = {"viu2": {}, "globocorp": {}}
    project_ids = set()
    for pair in mapping["rows"]:
        project = str(UUID(pair["projeto_id"]))
        if project in project_ids or pair["identity_quality"] != "selected_by_user_accepted_policy":
            raise ValueError("Consolidacao: identidade duplicada/incompativel")
        project_ids.add(project)
        for env, (account, board) in SCOPES.items():
            item = int(pair[env + "_item_id"])
            if (pair[env + "_account_id"], int(pair[env + "_board_id"])) != (account, board) or item <= 0:
                raise ValueError("Consolidacao: escopo do mapa divergente")
            if item in indices[env]:
                raise ValueError("Consolidacao: mapa nao e um para um")
            indices[env][item] = pair
    cutoffs = {r["corte_utc"] for r in new_rows}
    if len(cutoffs) != 1:
        raise ValueError("Consolidacao: corte novo ausente ou multiplo")
    cutoff = next(iter(cutoffs))
    timestamp(cutoff)
    current = {int(r["item_id"]) for r in new_rows}
    active = {p["projeto_id"] for p in mapping["rows"] if int(p["globocorp_item_id"]) in current}
    title_excluded = set()
    for env, source in (("viu2", old_rows), ("globocorp", new_rows)):
        for row in source:
            pair = indices[env].get(int(row["item_id"]))
            if pair and (motivos_exclusao(row.get("projeto_nome")) or (
                    env == "viu2" and (
                        (require_old_context and (int(row["board_id"]), int(row["item_id"])) not in old_inputs)
                        or motivos_input(old_inputs.get((int(row["board_id"]), int(row["item_id"]))))))):
                title_excluded.add(pair["projeto_id"])
    groups, excluded, seen = defaultdict(list), Counter(), set()
    for env, source in (("viu2", old_rows), ("globocorp", new_rows)):
        for r in source:
            item = int(r["item_id"])
            if int(r["board_id"]) != SCOPES[env][1]:
                raise ValueError("Consolidacao: quadro incorreto")
            key = (env, r["interval_id"])
            if key in seen:
                raise ValueError("Consolidacao: passagem repetida")
            seen.add(key)
            pair = indices[env].get(item)
            if not pair:
                excluded[env + ":sem_mapa"] += 1
                continue
            if pair["projeto_id"] in title_excluded:
                excluded[env + ":titulo_fora_escopo"] += 1
                continue
            if pair["projeto_id"] not in active:
                excluded[env + ":sem_item_na_gold_atual"] += 1
                continue
            old = env == "viu2"
            status = r["status_index"] if old else r["status_id"]
            if not old:
                prefix = "18429499488:status_19:"
                if not status.startswith(prefix):
                    raise ValueError("Consolidacao: codigo de status novo incompativel")
                status = status[len(prefix):]
            start, end = timestamp(r["entrada_status_utc"]), timestamp(r["saida_status_utc"])
            if end is not None and start is not None and end < start:
                raise ValueError("Consolidacao: intervalo invalido")
            if start is None and (old or r["qualidade_historico"] == "observed"):
                raise ValueError("Consolidacao: passagem observada sem inicio")
            if start is None:
                excluded[env + ":sem_entrada_comprovada"] += 1
                continue
            issues = ["validacao_negocio_pendente", "continuidade_entre_ambientes_nao_comprovada"]
            if not require_old_context:
                issues.append("contexto_input_nao_verificado")
            if old:
                issues.extend(json.loads(r["pendencias_json"]))
            if start is None:
                issues.append("referencia_sem_data_nao_e_passagem_comprovada")
            if end is None:
                issues.append("duracao_fechada_indisponivel")
            row = {
                "ordem_etapa": None, "projeto_nome": r["projeto_nome"], "status_nome": r["status_nome"],
                "entrada_status_local": r["entrada_status_local"], "saida_status_local": r["saida_status_local"],
                "duracao_horas": r["duracao_horas"] if start and end else None,
                "duracao_horas_uteis": r["duracao_horas_uteis"] if start and end else None,
                "marca_nome": None if old else r["marca_nome"], "talento_nome": None if old else r["talento_nome"],
                "responsavel_orcamento": None if old else r["responsavel_orcamento"],
                "marca_original": r["marca_original"] if old else None,
                "talento_original": r["talento_original"] if old else None,
                "eh_retorno": None, "retorno_observado_origem": r["retorno_observado"] if old else r["eh_retorno"],
                "projeto_id": pair["projeto_id"], "item_id": item, "board_id": SCOPES[env][1],
                "ambiente_origem": env, "conta_origem": SCOPES[env][0],
                "interval_id": str(uuid5(NAMESPACE, env + ":" + r["interval_id"])),
                "interval_id_origem": r["interval_id"], "item_id_viu2": int(pair["viu2_item_id"]),
                "item_id_globocorp": int(pair["globocorp_item_id"]), "ordem_origem": r["ordem_etapa"],
                "status_index": status, "tipo_registro": "passagem_observada" if start else "referencia_sem_evento",
                "qualidade_historico_origem": r["situacao_passagem"] if old else r["qualidade_historico"],
                "qualidade_identidade": pair["identity_quality"], "continuidade_validada": False,
                "elegivel_comparacao": False, "validacao_negocio": "pendente",
                "entrada_status_utc": r["entrada_status_utc"], "saida_status_utc": r["saida_status_utc"],
                "corte_globocorp_utc": cutoff, "cadastro_referencia_utc": r["cadastro_referencia_utc"],
                "versao_contrato": VERSION, "versao_calendario_origem": r["versao_calendario"],
                "pendencias_json": json.dumps(sorted(set(issues))),
                "registro_origem_json": json.dumps(r, ensure_ascii=False, sort_keys=True),
            }
            groups[pair["projeto_id"]].append(row)
    result, conflicts = [], 0
    for group in groups.values():
        timed = sorted((r for r in group if r["entrada_status_utc"]),
                       key=lambda r: (timestamp(r["entrada_status_utc"]), r["interval_id"]))
        times = Counter(timestamp(r["entrada_status_utc"]) for r in timed)
        overlapping = set()
        for i, left in enumerate(timed):
            end = timestamp(left["saida_status_utc"])
            for right in timed[i + 1:]:
                if not end or timestamp(right["entrada_status_utc"]) >= end:
                    break
                overlapping.update((left["interval_id"], right["interval_id"]))
        ambiguous_order = any(n > 1 for n in times.values())
        if ambiguous_order:
            excluded["consolidado:projeto_com_ordem_ambigua"] += len(group)
            continue
        for order, row in enumerate(timed, 1):
            issues = json.loads(row["pendencias_json"])
            if ambiguous_order:
                issues.append("ordem_temporal_ambigua")
            else:
                row["ordem_etapa"] = order
            if row["interval_id"] in overlapping:
                row["duracao_horas"] = row["duracao_horas_uteis"] = None
                issues.append("sobreposicao_temporal_duracao_bloqueada")
                conflicts += 1
            row["pendencias_json"] = json.dumps(sorted(set(issues)))
        annotate_closures(timed, terminal_labels)
        result.extend(group)
    result.sort(key=lambda r: (r["projeto_id"], r["ordem_etapa"] or 10**9, r["interval_id"]))
    calendar = BusinessCalendar("America/Sao_Paulo")
    for row in result:
        eligible = decision(row, calendar)["elegivel_kpi_etapa_candidato"]
        row["elegivel_comparacao"] = eligible
        row["validacao_negocio"] = "aprovado_etapa_origem_v1" if eligible else "nao_elegivel_etapa_origem_v1"
        row.update(consumption_project(row, calendar))
    trajectory_fields = trajectory_project(result)
    for row in result:
        row.update(trajectory_fields[row["interval_id"]])
    estimates = estimate_project(result, calendar)
    for row in result:
        row.update(estimates[row["interval_id"]])
        row.update(analysis_project(row))
    pricing = pricing_project(result, calendar)
    for row in result:
        row.update(pricing[row["interval_id"]])
    context_index = {}
    for item in current_context or []:
        if item['item_id'] in context_index:
            raise ValueError('Consolidacao: cadastro atual duplicado')
        context_index[item['item_id']] = item
    for row in result:
        context = context_index.get(row['item_id_globocorp'])
        if current_context is not None and context is None:
            raise ValueError('Consolidacao: item ausente do cadastro atual verificado')
        row['cadastro_atual_origem_json'] = json.dumps(context, ensure_ascii=False, sort_keys=True) if context else None
        row.update(context_project(row))
        row.update(talent_project(row))
    validate(result)
    trajectory_report = audit_trajectory(result)
    trajectory_report.pop("details")
    return result, {"rows": len(result), "projects": len({r["projeto_id"] for r in result}), "selected_map_pairs": len(project_ids),
                    "trajectory_audit": trajectory_report,
                    "mapped_projects_absent_current_gold": len(project_ids - active),
                    "rows_by_origin": dict(Counter(r["ambiente_origem"] for r in result)),
                    "rows_by_type": dict(Counter(r["tipo_registro"] for r in result)),
                    "excluded_source_rows": dict(excluded), "overlapping_rows": conflicts,
                    "terminal_rows": sum(r["status_terminal"] is True for r in result),
                    "closed_source_cycles_with_hours": sum(r["tempo_ciclo_observado_horas"] is not None for r in result),
                    "proven_source_reopenings": sum(r["reabertura_comprovada_origem"] for r in result),
                    "terminal_labels": list(terminal_labels),
                    "title_scope_version": TITLE_SCOPE_VERSION,
                    "title_excluded_selected_projects": len(title_excluded),
                    "kpi_stage_eligible_rows": sum(r["elegivel_comparacao"] for r in result),
                    "kpi_cross_environment_approved": False, "daily_integration_deployed": False}


def validate(rows):
    seen = set()
    calendar = BusinessCalendar("America/Sao_Paulo")
    if len({r.get("versao_contrato") for r in rows}) > 1:
        raise ValueError("Consolidacao: contratos misturados")
    for r in rows:
        fields = fields_for(r.get("versao_contrato"))
        if set(r) != set(fields) or r["interval_id"] in seen:
            raise ValueError("Consolidacao: schema/chave invalido")
        seen.add(r["interval_id"])
        for field, (kind, required) in fields.items():
            value = r[field]
            if value is None:
                if required:
                    raise ValueError("Consolidacao: obrigatorio nulo")
                continue
            if kind == "INTEGER" and (type(value) is not int or not 0 < value < 2**63):
                raise ValueError("Consolidacao: inteiro invalido")
            if kind == "BOOLEAN" and type(value) is not bool:
                raise ValueError("Consolidacao: booleano invalido")
            if kind in {"STRING", "DATETIME", "TIMESTAMP"} and not isinstance(value, str):
                raise ValueError("Consolidacao: texto/data invalido")
            if kind == "TIMESTAMP":
                timestamp(value)
            if kind == "FLOAT" and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError("Consolidacao: horas invalidas")
        if r["continuidade_validada"] or r["eh_retorno"] is not None:
            raise ValueError("Consolidacao: aprovacao/retorno global indevido")
        if r["versao_contrato"] == LEGACY_VERSION:
            # Read/reconcile the previous active snapshot during controlled upgrade.
            if r["elegivel_comparacao"] or r["validacao_negocio"] != "pendente":
                raise ValueError("Consolidacao: aprovacao legada indevida")
        elif r["versao_contrato"] in (STAGE_VERSION, CONSUMPTION_VERSION, TRAJECTORY_VERSION, ESTIMATE_VERSION, ANALYSIS_VERSION, PRICING_VERSION, VERSION):
            eligible = decision(r, calendar)["elegivel_kpi_etapa_candidato"]
            state = "aprovado_etapa_origem_v1" if eligible else "nao_elegivel_etapa_origem_v1"
            if r["elegivel_comparacao"] != eligible or r["validacao_negocio"] != state:
                raise ValueError("Consolidacao: elegibilidade de etapa divergente")
            if r["versao_contrato"] in (CONSUMPTION_VERSION, TRAJECTORY_VERSION, ESTIMATE_VERSION, ANALYSIS_VERSION, PRICING_VERSION, VERSION):
                if any(r[k] != v for k, v in consumption_project(r, calendar).items()):
                    raise ValueError("Consolidacao: campos de consumo divergentes")
        else:
            raise ValueError("Consolidacao: contrato divergente")
        if r["status_terminal"] is True:
            if r["finalizacao_observada_utc"] != r["entrada_status_utc"] or any(
                    r[k] is not None for k in ("duracao_horas", "duracao_horas_uteis")):
                raise ValueError("Consolidacao: terminal acumulou SLA apos fechamento")
        elif r["finalizacao_observada_utc"] is not None or r["tempo_ciclo_observado_horas"] is not None:
            raise ValueError("Consolidacao: fechamento/total sem terminal")
        if r["entrada_status_utc"] is None or r["ordem_etapa"] is None:
            raise ValueError("Consolidacao: referencia sem data/ordem nao pertence ao SLA")
        if r["duracao_horas"] is not None:
            start, end = timestamp(r["entrada_status_utc"]), timestamp(r["saida_status_utc"])
            if not start or not end or abs(round((end - start).total_seconds() / 3600, 3) - r["duracao_horas"]) > 0.001:
                raise ValueError("Consolidacao: horas sem limites comprovados")
            if r["duracao_horas_uteis"] is not None and r["duracao_horas_uteis"] > r["duracao_horas"] + 0.001:
                raise ValueError("Consolidacao: horas uteis excedem corridas")
    audit_trajectory(rows)
    if rows and rows[0]["versao_contrato"] in (TRAJECTORY_VERSION, ESTIMATE_VERSION, ANALYSIS_VERSION, PRICING_VERSION, VERSION):
        expected = trajectory_project(rows)
        for row in rows:
            if any(row[k] != v for k, v in expected[row["interval_id"]].items()):
                raise ValueError("Consolidacao: campos de trajetoria divergentes")
    if rows and rows[0]["versao_contrato"] in (ESTIMATE_VERSION, ANALYSIS_VERSION, PRICING_VERSION, VERSION):
        expected = estimate_project(rows, calendar)
        for row in rows:
            if any(row[k] != v for k, v in expected[row["interval_id"]].items()):
                raise ValueError("Consolidacao: campos de estimativa divergentes")
    if rows and rows[0]["versao_contrato"] in (ANALYSIS_VERSION, PRICING_VERSION, VERSION):
        for row in rows:
            if any(row[k] != v for k, v in analysis_project(row).items()):
                raise ValueError("Consolidacao: duracao de analise divergente")
    if rows and rows[0]["versao_contrato"] in (PRICING_VERSION, VERSION):
        for row in rows:
            if any(row[k] != v for k, v in context_project(row).items()):
                raise ValueError('Consolidacao: cadastro atual divergente')
        expected = pricing_project(rows, calendar)
        for row in rows:
            if any(row[k] != v for k, v in expected[row["interval_id"]].items()):
                raise ValueError("Consolidacao: precificacao divergente")
    if rows and rows[0]['versao_contrato'] == VERSION:
        for row in rows:
            if any(row[k] != value for k, value in talent_project(row).items()):
                raise ValueError('Consolidacao: talentos atuais divergentes')
