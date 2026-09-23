"""Project-level audit; never infer missing transitions or approve total SLA."""

import json
from collections import Counter, defaultdict
from datetime import UTC, datetime

FIELDS = {
    "quantidade_passagens_projeto": ("INTEGER", True),
    "qualidade_trajetoria": ("STRING", True),
    "limitacoes_trajetoria_json": ("STRING", True),
    "eh_ultima_etapa_observada": ("BOOLEAN", True),
    "versao_regra_trajetoria": ("STRING", True),
}


def instant(value):
    if value is None:
        return None
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.utcoffset() is None:
        raise ValueError("Trajetoria: timestamp sem fuso")
    return result.astimezone(UTC)


def audit(rows):
    """Reject structural corruption; report evidence limitations without deleting rows.

    A connected timeline is necessary, not sufficient, for a complete history.
    This audit deliberately never grants project-total or ML eligibility.
    """
    groups = defaultdict(list)
    for row in rows:
        groups[row["projeto_id"]].append(row)
    projects = []
    for project_id, group in sorted(groups.items()):
        ordered = sorted(group, key=lambda r: r["ordem_etapa"])
        if [r["ordem_etapa"] for r in ordered] != list(range(1, len(group) + 1)):
            raise ValueError("Trajetoria: ordem duplicada ou descontigua")
        pairs = {(r["item_id_viu2"], r["item_id_globocorp"]) for r in ordered}
        if len(pairs) != 1:
            raise ValueError("Trajetoria: identidade inconsistente no projeto")
        starts = [instant(r["entrada_status_utc"]) for r in ordered]
        if any(t is None for t in starts) or any(a >= b for a, b in zip(starts, starts[1:], strict=False)):
            raise ValueError("Trajetoria: ordem nao corresponde a cronologia")
        reasons = set()
        gaps = boundaries = 0
        for i, row in enumerate(ordered):
            env = row["ambiente_origem"]
            if env not in {"viu2", "globocorp"} or row["item_id"] != row["item_id_" + env]:
                raise ValueError("Trajetoria: item diverge da origem mapeada")
            end = instant(row["saida_status_utc"])
            if end is not None and end < starts[i]:
                raise ValueError("Trajetoria: saida anterior a entrada")
            if not row.get("status_nome") or row.get("status_terminal") is None:
                reasons.add("status_sem_classificacao")
            if i:
                previous = ordered[i - 1]
                previous_end = instant(previous["saida_status_utc"])
                if previous_end != starts[i]:
                    gaps += 1
                    reasons.add("transicao_sem_continuidade_temporal")
                if previous["ambiente_origem"] != env:
                    boundaries += 1
                    reasons.add("fronteira_entre_ambientes_nao_comprovada")
                if previous_end is not None and previous_end > starts[i]:
                    reasons.add("sobreposicao_temporal")
        if len(ordered) == 1:
            reasons.add("passagem_unica")
        if (ordered[0].get("status_nome") or "").strip().casefold() != "entrada":
            reasons.add("inicio_em_entrada_nao_observado")
        if ordered[-1].get("status_terminal") is not True:
            reasons.add("ultimo_registro_nao_e_encerramento_observado")
        projects.append({
            "projeto_id": project_id,
            "passagens": len(ordered),
            "status_distintos_conhecidos": len({r["status_nome"] for r in ordered if r["status_nome"]}),
            "transicoes_sem_continuidade_temporal": gaps,
            "fronteiras_entre_ambientes": boundaries,
            "somente_terminal": all(r.get("status_terminal") is True for r in ordered),
            "motivos": sorted(reasons),
        })
    counts = Counter(reason for p in projects for reason in p["motivos"])
    return {"policy": "auditoria-trajetoria-v1", "projects": len(projects),
            "rows": len(rows), "projects_by_reason": dict(sorted(counts.items())),
            "terminal_only_projects": sum(p["somente_terminal"] for p in projects),
            "projects_without_detected_limitations": sum(not p["motivos"] for p in projects),
            "total_sla_approved": False, "details": projects}


def project(rows):
    """Pure additive projection, indexed by interval ID; no fabricated dates."""
    report = audit(rows)
    details = {p["projeto_id"]: p for p in report["details"]}
    result = {}
    for row in rows:
        info = details[row["projeto_id"]]
        if row["interval_id"] in result:
            raise ValueError("Trajetoria: passagem duplicada")
        result[row["interval_id"]] = {
            "quantidade_passagens_projeto": info["passagens"],
            "qualidade_trajetoria": ("historico_com_limitacoes" if info["motivos"]
                                      else "sequencia_observada_sem_lacunas_detectadas"),
            "limitacoes_trajetoria_json": json.dumps(info["motivos"], ensure_ascii=False),
            "eh_ultima_etapa_observada": row["ordem_etapa"] == info["passagens"],
            "versao_regra_trajetoria": report["policy"],
        }
    return result
