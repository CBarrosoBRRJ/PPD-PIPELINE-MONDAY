"""Candidate, fail-closed eligibility for source-local completed-stage KPIs.

Does not approve cross-account continuity or mutate the published v2 contract.
Calendar is explicitly supplied: unknown versions cannot silently use defaults.
"""

import json
import math
from datetime import datetime

VERSION = "kpi-etapa-origem-v1"
NON_BLOCKING = frozenset({
    "validacao_negocio_pendente", "continuidade_entre_ambientes_nao_comprovada",
    "business_eligibility_pending", "project_mapping_pending", "migration_boundary_pending",
})
LABEL_QUALITY = frozenset({"label_observed_at_exit_previous_value", "label_observed_at_start"})


def decision(row, calendar):
    """Return candidate eligibility; upstream title/Input scope must be verified.

Unknown issues block instead of inheriting an optimistic default. Generic review
flags above remain on the source; they are not globally marked as resolved.
"""
    reasons = set()
    issues = json.loads(row["pendencias_json"])
    source = json.loads(row["registro_origem_json"])
    if not isinstance(issues, list) or any(not isinstance(i, str) for i in issues):
        raise ValueError("KPI: invalid issues")
    if not isinstance(source, dict):
        raise ValueError("KPI: invalid source lineage")
    reasons.update(set(issues) - NON_BLOCKING)
    if row["ambiente_origem"] not in {"viu2", "globocorp"}:
        reasons.add("origem_desconhecida")
    if row.get("status_terminal") is not False:
        reasons.add("terminal_ou_classificacao_desconhecida")
    if not (row.get("status_nome") or "").strip():
        reasons.add("rotulo_ausente")
    if row.get("situacao_sla_registro") != "passagem_com_saida_observada":
        reasons.add("passagem_nao_fechada")
    if row.get("versao_calendario_origem") != calendar.version:
        reasons.add("calendario_nao_validado")
    if row["ambiente_origem"] == "viu2":
        if source.get("situacao_passagem") != "observed_closed_candidate":
            reasons.add("historico_nao_observado")
        if source.get("qualidade_rotulo") not in LABEL_QUALITY:
            reasons.add("rotulo_sem_evidencia_aprovada")
        for field in ("eventos_suporte_json", "eventos_saida_json"):
            evidence = json.loads(source.get(field, "[]"))
            if not isinstance(evidence, list) or not evidence or any(
                not isinstance(e, str) or not e.strip() for e in evidence
            ):
                reasons.add("evento_limite_ausente")
    else:
        if source.get("qualidade_historico") != "observed":
            reasons.add("historico_nao_observado")
        if source.get("elegivel_comparacao") is not True:
            reasons.add("origem_nao_elegivel")
    start, end = row.get("entrada_status_utc"), row.get("saida_status_utc")
    if not start or not end:
        reasons.add("limite_temporal_ausente")
    else:
        start, end = (datetime.fromisoformat(v.replace("Z", "+00:00")) for v in (start, end))
        if start.utcoffset() is None or end.utcoffset() is None or end < start:
            raise ValueError("KPI: invalid temporal boundaries")
        for field, expected in (
            ("duracao_horas", round((end - start).total_seconds() / 3600, 3)),
            ("duracao_horas_uteis", round(calendar.hours(start, end), 3)),
        ):
            value = row.get(field)
            if value is None:
                reasons.add("duracao_indisponivel")
            elif type(value) not in (int, float) or not math.isfinite(value) or abs(value - expected) > 1e-8:
                reasons.add("duracao_nao_reconciliada")
    return {"politica": VERSION, "elegivel_kpi_etapa_candidato": not reasons,
            "motivos": sorted(reasons), "continuidade_entre_ambientes_aprovada": False}
