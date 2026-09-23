"""Opt-in analytical hypothesis; never replaces observed exits or official KPI."""

import json
from collections import defaultdict

from monday_sla_orcamento.trajectory import audit, instant

VERSION = "estimativa-proxima-etapa-v1"
FIELDS = {
    "saida_estimada_utc": ("TIMESTAMP", False),
    "saida_estimada_local": ("DATETIME", False),
    "duracao_estimada_horas": ("FLOAT", False),
    "duracao_estimada_horas_uteis": ("FLOAT", False),
    "metodo_estimativa": ("STRING", True),
    "interval_id_referencia_estimativa": ("STRING", False),
    "versao_regra_estimativa": ("STRING", True),
    "versao_calendario_estimativa": ("STRING", False),
}


def project(rows, calendar):
    report = audit(rows)
    blocked = {p["projeto_id"] for p in report["details"] if "sobreposicao_temporal" in p["motivos"]}
    groups = defaultdict(list)
    result = {}
    for row in rows:
        groups[row["projeto_id"]].append(row)
        result[row["interval_id"]] = {name: None for name in FIELDS}
        result[row["interval_id"]].update(metodo_estimativa="nao_aplicavel", versao_regra_estimativa=VERSION)
        if "sobreposicao_temporal_duracao_bloqueada" in json.loads(row["pendencias_json"]):
            blocked.add(row["projeto_id"])
    for project_id, group in groups.items():
        if project_id in blocked:
            continue
        ordered = sorted(group, key=lambda r: r["ordem_etapa"])
        for previous, following in zip(ordered, ordered[1:], strict=False):
            if (previous["status_terminal"] is not False or following["status_terminal"] is None
                    or previous["saida_status_utc"] is not None
                    or previous["ambiente_origem"] != "viu2" or following["ambiente_origem"] != "globocorp"
                    or any(r["qualidade_identidade"] != "selected_by_user_accepted_policy"
                           for r in (previous, following))
                    or not previous["status_nome"] or not following["status_nome"]
                    or previous["status_nome"].strip().casefold() == following["status_nome"].strip().casefold()):
                continue
            start, end = instant(previous["entrada_status_utc"]), instant(following["entrada_status_utc"])
            if not start < end <= instant(previous["corte_globocorp_utc"]):
                continue
            result[previous["interval_id"]].update(
                saida_estimada_utc=end.isoformat(timespec="microseconds"),
                saida_estimada_local=end.astimezone(calendar.zone).replace(tzinfo=None).isoformat(timespec="microseconds"),
                duracao_estimada_horas=round((end - start).total_seconds() / 3600, 3),
                duracao_estimada_horas_uteis=round(calendar.hours(start, end), 3),
                metodo_estimativa="estimada_pela_proxima_etapa_entre_ambientes",
                interval_id_referencia_estimativa=following["interval_id"],
                versao_calendario_estimativa=calendar.version,
            )
    return result
