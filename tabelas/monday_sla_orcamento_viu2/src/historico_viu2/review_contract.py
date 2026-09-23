"""Versioned private review export. Deliberately not the deployed SLA contract."""

import math
from collections import defaultdict
from uuid import NAMESPACE_URL, uuid5
from zoneinfo import ZoneInfo

from monday_comum.escopo_sla import filtrar_projetos
from sls_orcamento_ppd.utils.time import parse_timestamp

VERSION = "sla-viu2-review-v1"
TARGET = "monday_sla_orcamento_viu2"
FIELDS = {
    "ordem_etapa": ("INTEGER", True), "projeto_nome": ("STRING", False),
    "status_nome": ("STRING", False), "entrada_status_local": ("DATETIME", True),
    "saida_status_local": ("DATETIME", False), "duracao_horas": ("FLOAT", False),
    "duracao_horas_uteis": ("FLOAT", False),
    "marca_original": ("STRING", False), "talento_original": ("STRING", False),
    "conta_origem": ("STRING", True), "ambiente_origem": ("STRING", True),
    "board_id": ("INTEGER", True), "item_id": ("INTEGER", True),
    "interval_id": ("STRING", True), "projeto_id": ("STRING", False),
    "status_index": ("STRING", True), "situacao_passagem": ("STRING", True),
    "entrada_status_utc": ("TIMESTAMP", True), "saida_status_utc": ("TIMESTAMP", False),
    "cadastro_referencia_utc": ("TIMESTAMP", False), "origem_atributos": ("STRING", True),
    "qualidade_rotulo": ("STRING", True), "retorno_observado": ("BOOLEAN", True),
    "elegivel_comparacao": ("BOOLEAN", True), "validacao_negocio": ("STRING", True),
    "versao_contrato": ("STRING", True), "versao_calendario": ("STRING", True),
    "eventos_suporte_json": ("STRING", True), "eventos_saida_json": ("STRING", True),
    "pendencias_json": ("STRING", True),
}
SITUATIONS = {"observed_closed_candidate", "no_observed_exit", "interrupted_by_evidence_gap"}


def schema():
    return [{"name": k, "type": kind, "mode": "REQUIRED" if required else "NULLABLE"}
            for k, (kind, required) in FIELDS.items()]


def project_review(document):
    import json

    grouped = defaultdict(list)
    inputs = {}
    unverified = set()
    for passage in document["passages"]:
        if passage["source_account_id"] != "5890468" or passage["source_board_id"] != "18393336134":
            raise ValueError("Contrato de revisão: origem incorreta")
        grouped[passage["source_item_id"]].append(passage)
        if passage.get("tipo_input_verificado") is True:
            inputs[(18393336134, int(passage["source_item_id"]))] = passage.get("tipo_input")
        else:
            unverified.add((18393336134, int(passage["source_item_id"])))
    for key in unverified:
        inputs.pop(key, None)
    rows = []
    zone = ZoneInfo("America/Sao_Paulo")
    for item, passages in sorted(grouped.items()):
        passages.sort(key=lambda p: parse_timestamp(p["entrada_status_utc"]))
        for order, p in enumerate(passages, 1):
            start = parse_timestamp(p["entrada_status_utc"])
            end = parse_timestamp(p["saida_status_utc"]) if p["saida_status_utc"] else None
            key = f"viu2:5890468:18393336134:{item}:{p['status_index']}:{start.isoformat()}"
            issues = ["business_eligibility_pending", "project_mapping_pending", "migration_boundary_pending"]
            if p["status_nome"] is None:
                issues.append("historical_label_unavailable")
            if p["attribute_source"] == "unavailable":
                issues.append("context_unavailable")
            if p["schema_event_ids_during_passage"]:
                issues.append("status_schema_review_pending")
            if p["quality"] != "observed_closed_candidate":
                issues.append(p["quality"])
            rows.append({
                "ordem_etapa": order, "projeto_nome": p["projeto_nome"], "status_nome": p["status_nome"],
                "entrada_status_local": start.astimezone(zone).replace(tzinfo=None).isoformat(),
                "saida_status_local": end.astimezone(zone).replace(tzinfo=None).isoformat() if end else None,
                "duracao_horas": p["duracao_horas"], "duracao_horas_uteis": p["duracao_horas_uteis"],
                "marca_original": p["marca_original"], "talento_original": p["talento_original"],
                "conta_origem": "5890468", "ambiente_origem": "viu2", "board_id": 18393336134,
                "item_id": int(item), "interval_id": str(uuid5(NAMESPACE_URL, VERSION + ":" + key)),
                "projeto_id": None, "status_index": p["status_index"], "situacao_passagem": p["quality"],
                "entrada_status_utc": start.isoformat(), "saida_status_utc": end.isoformat() if end else None,
                "cadastro_referencia_utc": p["cadastro_referencia_utc"], "origem_atributos": p["attribute_source"],
                "qualidade_rotulo": p["status_label_quality"], "retorno_observado": p["observed_visit_number"] > 1,
                "elegivel_comparacao": False, "validacao_negocio": "pendente",
                "versao_contrato": VERSION, "versao_calendario": document["calendar"]["version"],
                "eventos_suporte_json": json.dumps(p["supporting_event_ids"], separators=(",", ":")),
                "eventos_saida_json": json.dumps(p["end_event_ids"], separators=(",", ":")),
                "pendencias_json": json.dumps(issues, separators=(",", ":")),
            })
    rows = filtrar_projetos(rows, inputs)
    validate(rows)
    return rows


def validate(rows):
    import json
    from datetime import datetime

    from sls_orcamento_ppd.rules.business_time import BusinessCalendar

    seen, grouped = set(), defaultdict(list)
    calendar = BusinessCalendar("America/Sao_Paulo")
    for row in rows:
        if set(row) != set(FIELDS):
            raise ValueError("Contrato de revisão: campos incompatíveis")
        for name, (kind, required) in FIELDS.items():
            value = row[name]
            if value is None:
                if required:
                    raise ValueError("Contrato de revisão: campo obrigatório ausente")
                continue
            valid = {
                "STRING": isinstance(value, str), "BOOLEAN": type(value) is bool,
                "INTEGER": type(value) is int and 0 < value < 2**63,
                "FLOAT": type(value) in (int, float) and math.isfinite(value) and value >= 0,
                "TIMESTAMP": isinstance(value, str), "DATETIME": isinstance(value, str),
            }[kind]
            if not valid or (required and kind == "STRING" and not value.strip()):
                raise ValueError("Contrato de revisão: tipo inválido")
            if kind == "TIMESTAMP":
                parse_timestamp(value)
            if kind == "DATETIME" and datetime.fromisoformat(value).tzinfo is not None:
                raise ValueError("Contrato de revisão: data local com fuso")
        if (row["ambiente_origem"], row["conta_origem"], row["board_id"]) != ("viu2", "5890468", 18393336134):
            raise ValueError("Contrato de revisão: escopo inválido")
        if row["interval_id"] in seen:
            raise ValueError("Contrato de revisão: chave repetida")
        seen.add(row["interval_id"])
        grouped[row["item_id"]].append(row)
        if (row["versao_contrato"] != VERSION or row["elegivel_comparacao"] is not False or
                row["validacao_negocio"] != "pendente" or row["projeto_id"] is not None):
            raise ValueError("Contrato de revisão: aprovação não permitida")
        if row["situacao_passagem"] not in SITUATIONS:
            raise ValueError("Contrato de revisão: situação inválida")
        start = parse_timestamp(row["entrada_status_utc"])
        end = parse_timestamp(row["saida_status_utc"]) if row["saida_status_utc"] else None
        key = f"viu2:5890468:18393336134:{row['item_id']}:{row['status_index']}:{start.isoformat()}"
        if row["interval_id"] != str(uuid5(NAMESPACE_URL, VERSION + ":" + key)):
            raise ValueError("Contrato de revisão: chave não corresponde à evidência")
        if row["versao_calendario"] != calendar.version:
            raise ValueError("Contrato de revisão: calendário incompatível")
        for utc, local in ((start, row["entrada_status_local"]), (end, row["saida_status_local"])):
            expected_local = utc.astimezone(ZoneInfo("America/Sao_Paulo")).replace(tzinfo=None).isoformat() if utc else None
            if local != expected_local:
                raise ValueError("Contrato de revisão: data local divergente")
        if row["situacao_passagem"] == "observed_closed_candidate":
            if end is None or end <= start or row["duracao_horas"] is None or row["duracao_horas_uteis"] is None:
                raise ValueError("Contrato de revisão: passagem encerrada inconsistente")
            expected = round((end - start).total_seconds() / 3600, 3)
            if abs(expected - row["duracao_horas"]) > 1e-8 or row["duracao_horas_uteis"] > row["duracao_horas"]:
                raise ValueError("Contrato de revisão: duração divergente")
            if round(calendar.hours(start, end), 3) != row["duracao_horas_uteis"]:
                raise ValueError("Contrato de revisão: horas úteis divergentes")
            if not json.loads(row["eventos_saida_json"]):
                raise ValueError("Contrato de revisão: saída sem evento")
        elif any(row[k] is not None for k in ("saida_status_utc", "duracao_horas", "duracao_horas_uteis")):
            raise ValueError("Contrato de revisão: duração/saída sem evidência")
        for name in ("eventos_suporte_json", "eventos_saida_json", "pendencias_json"):
            value = json.loads(row[name])
            if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
                raise ValueError("Contrato de revisão: linhagem/pendências inválidas")
            if name != "eventos_saida_json" and not value:
                raise ValueError("Contrato de revisão: evidência/pendência ausente")
    for group in grouped.values():
        ordered = sorted(group, key=lambda r: r["ordem_etapa"])
        if [r["ordem_etapa"] for r in ordered] != list(range(1, len(group) + 1)):
            raise ValueError("Contrato de revisão: sequência inválida")
        for left, right in zip(ordered, ordered[1:], strict=False):
            if parse_timestamp(left["entrada_status_utc"]) >= parse_timestamp(right["entrada_status_utc"]):
                raise ValueError("Contrato de revisão: ordem temporal inválida")
            if left["saida_status_utc"] and parse_timestamp(left["saida_status_utc"]) > parse_timestamp(right["entrada_status_utc"]):
                raise ValueError("Contrato de revisão: intervalos sobrepostos")
