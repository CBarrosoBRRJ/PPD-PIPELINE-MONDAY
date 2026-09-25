"""Candidato offline: ciclos vivos. Nao altera contratos/publicacoes v17."""

import json
from collections import defaultdict
from uuid import NAMESPACE_URL, uuid5

from monday_sla_orcamento.pricing import TERMINALS, WORK, normalize
from monday_sla_orcamento.trajectory import instant

RULE = "ciclos-continuos-v1"
CATEGORIES = ("operacao", "feedback", "terceiros", "standby", "terminal", "desconhecido")


def bridge(left, right, cutoff):
    """Hipotese de permanencia, nunca prova de continuidade observada."""
    return (
        left["ambiente_origem"] == "viu2" and right["ambiente_origem"] == "globocorp"
        and left.get("saida_status_utc") is None
        and category(left.get("status_nome")) not in {"terminal", "desconhecido"}
        and category(right.get("status_nome")) != "desconhecido"
        and all(r.get("qualidade_identidade") == "selected_by_user_accepted_policy"
                for r in (left, right))
        and all(left.get(k) is not None and left.get(k) == right.get(k)
                for k in ("item_id_viu2", "item_id_globocorp"))
        and instant(left["entrada_status_utc"]) < instant(right["entrada_status_utc"]) <= cutoff
    )


def category(label):
    value = normalize(label)
    if value in WORK:
        return "operacao"
    if value == "aguardando feedback":
        return "feedback"
    if value == "em elaboração - retorno marca/executivo":
        return "terceiros"
    if value == "standby":
        return "standby"
    return "terminal" if value in TERMINALS else "desconhecido"


def confirmed_open_at_cut(row, cutoff, calendar):
    """Use verified closed-day Gold evidence, never a later backlog snapshot."""
    if row['ambiente_origem'] != 'globocorp':
        return False
    source = json.loads(row.get('registro_origem_json', '{}'))
    return (source.get('qualidade_historico') == 'observed'
        and source.get('intervalo_aberto') is True
        and source.get('eh_ultimo_registro') is True
        and source.get('status_atual_divergente') is False
        and source.get('tempo_status_atual_horas') is not None
        and source.get('versao_calendario') == calendar.version
        and source.get('interval_id') is not None
        and source.get('interval_id') == row.get('interval_id_origem')
        and source.get('item_id') == row.get('item_id_globocorp')
        and source.get('saida_status_utc') is None
        and instant(source.get('corte_utc')) == cutoff
        and instant(source.get('entrada_status_utc')) == instant(row['entrada_status_utc'])
        and normalize(source.get('status_nome')) == normalize(row.get('status_nome')))


def build(rows, calendar, *, cut):
    """Input: trajetoria PRE filtro v17, IDs preservados, corte explicito UTC.

    Requer Entrada como primeiro status conhecido. Nenhuma criacao de vinculos.
    Troca de ambiente preserva ciclo, mas nao certifica duracao desconhecida.
    Ciclo fecha no Feedback; reabre na proxima etapa operacional. Standby e
    terceiros nao abrem novo ciclo por si so. Entrada repetida nao apaga trabalho.
    Aberto ate corte e idade, nao duracao encerrada nem entrega observada.
    """
    cutoff = instant(cut)
    if cutoff is None:
        raise ValueError("Ciclos: corte obrigatorio")
    groups, seen = defaultdict(list), set()
    for row in rows:
        if not row.get("interval_id") or row["interval_id"] in seen:
            raise ValueError("Ciclos: chave ausente/duplicada")
        seen.add(row["interval_id"])
        groups[row["projeto_id"]].append(row)
    passages, cycles, excluded = [], [], []
    for project, group in sorted(groups.items()):
        group.sort(key=lambda r: (instant(r["entrada_status_utc"]), r["interval_id"]))
        starts = [instant(r["entrada_status_utc"]) for r in group]
        if any(t > cutoff for t in starts) or any(a >= b for a, b in zip(starts, starts[1:], strict=False)):
            raise ValueError("Ciclos: cronologia invalida")
        overlapping = any(
            instant(left["saida_status_utc"]) is not None
            and instant(left["saida_status_utc"]) > starts[i + 1]
            for i, left in enumerate(group[:-1]))
        known = [i for i, r in enumerate(group) if normalize(r.get("status_nome"))]
        if not known or normalize(group[known[0]]["status_nome"]) != "entrada":
            excluded.append({"projeto_id": project, "motivo": "sem_entrada_inicial",
                             "passagens": len(group)})
            continue
        first = known[0]
        if any(instant(r["saida_status_utc"]) is not None
               and instant(r["saida_status_utc"]) > starts[first] for r in group[:first]):
            excluded.append({"projeto_id": project, "motivo": "prefixo_nulo_sobreposto",
                             "passagens": len(group)})
            continue
        current = None
        project_cycles = []
        visits = defaultdict(int)
        permanence = None
        for i, row in enumerate(group):
            start, end = starts[i], instant(row["saida_status_utc"])
            kind = category(row.get("status_nome"))
            issues = []
            same_previous = i > first and normalize(group[i - 1].get("status_nome")) == normalize(row.get("status_nome"))
            if not same_previous:
                permanence = row["interval_id"]
                if i >= first:
                    visits[normalize(row.get("status_nome"))] += 1
            estimated_boundary = i > first and not overlapping and bridge(group[i - 1], row, cutoff)
            if end is not None and (end < start or end > cutoff):
                raise ValueError("Ciclos: saida fora da janela")
            if i and i >= first:
                prev = group[i - 1]
                if i > first and instant(prev["saida_status_utc"]) != start:
                    issues.append("transicao_estimada_migracao" if estimated_boundary
                                  else "transicao_sem_continuidade_observada")
                if i > first and prev["ambiente_origem"] != row["ambiente_origem"]:
                    issues.append("fronteira_entre_ambientes")
            if kind == "desconhecido" and i >= first:
                issues.append("status_desconhecido")
            if kind == "feedback":
                source = json.loads(row.get("registro_origem_json", "{}"))
                observed = (source.get("qualidade_historico") == "observed"
                    if row["ambiente_origem"] == "globocorp" else
                    source.get("qualidade_rotulo") in {
                        "label_observed_at_start", "label_observed_at_exit_previous_value"})
                if not observed:
                    issues.append("entrega_sem_evidencia_de_rotulo")
            opening = kind == "operacao" and i >= first and current is None
            if opening:
                current = {"projeto_id": project,
                    "ciclo_id": str(uuid5(NAMESPACE_URL, f"{RULE}/{project}/{row['interval_id']}")),
                    "numero_ciclo": len(project_cycles) + 1,
                    "tipo_ciclo": "primeira_elaboracao" if not project_cycles else "revisao_reabertura",
                    "interval_id_inicio": row["interval_id"], "interval_id_fim": None,
                    "item_id_viu2": row.get("item_id_viu2"),
                    "item_id_globocorp": row.get("item_id_globocorp"),
                    "inicio_utc": row["entrada_status_utc"], "fim_utc": None,
                    "situacao": "em_andamento", "motivos": [], "passagens": [],
                    "versao_regra": RULE, "corte_utc": cutoff.isoformat()}
                project_cycles.append(current)
            assigned = current
            if current is not None:
                # Lacuna da espera anterior nao invalida o novo trabalho observado.
                if not opening:
                    current["motivos"].extend(issues)
                if kind in {"feedback", "terminal"}:
                    current["fim_utc"] = row["entrada_status_utc"]
                    current["interval_id_fim"] = row["interval_id"]
                    current["situacao"] = "entregue" if kind == "feedback" else "interrompido"
                    current = None
            provenance, right = "indisponivel", None
            if i < first:
                provenance = "prefixo_nulo"
            elif kind == "terminal":
                provenance = "nao_operacional_terminal"
            elif end is not None and row.get("elegivel_comparacao") is True:
                if row.get("versao_calendario_origem") == calendar.version:
                    right, provenance = end, "observada"
                else:
                    issues.append("calendario_divergente")
            elif end is None and i + 1 < len(group) and not overlapping and bridge(row, group[i + 1], cutoff):
                right, provenance = starts[i + 1], "estimada_migracao"
            elif end is None and i == len(group) - 1 and kind != "desconhecido":
                # Precisa de confirmacao do estado no corte, nao apenas snapshot atual posterior.
                if row.get("estado_confirmado_no_corte") is True or confirmed_open_at_cut(row, cutoff, calendar):
                    right, provenance = cutoff, "idade_aberta_no_corte"
            if right is None and i >= first and kind not in {"terminal"}:
                issues.append("duracao_nao_comprovada")
            passage = {"projeto_id": project, "interval_id": row["interval_id"],
                "ambiente_origem": row["ambiente_origem"], "categoria": kind,
                "grupo_permanencia_id": permanence,
                "eh_continuacao_mesmo_status": same_previous,
                "eh_retorno_status": i >= first and not same_previous and visits[normalize(row.get("status_nome"))] > 1,
                "ciclo_id": assigned["ciclo_id"] if assigned else None,
                "inicio_utc": row["entrada_status_utc"],
                "saida_observada_utc": row["saida_status_utc"],
                "saida_estimada_utc": right.isoformat() if provenance == "estimada_migracao" else None,
                "referencia_ate_utc": right.isoformat() if right is not None else None,
                "origem_duracao": provenance,
                "horas_corridas": round((right - start).total_seconds() / 3600, 3)
                    if right is not None else None,
                "horas_uteis": round(calendar.hours(start, right), 3)
                    if right is not None else None,
                "motivos": sorted(set(issues)), "versao_calendario": calendar.version}
            passages.append(passage)
            if assigned is not None and kind not in {"feedback", "terminal"}:
                assigned["passagens"].append(passage)
                assigned["motivos"].extend(issue for issue in issues if not opening or issue not in {
                    "transicao_sem_continuidade_observada", "transicao_estimada_migracao", "fronteira_entre_ambientes"})
        for cycle in project_cycles:
            members = cycle.pop("passagens")
            # Espera apos entrega pertence a analise por passagem, nao ao trabalho do ciclo.
            work = [r for r in members if r["categoria"] == "operacao"]
            cycle["motivos"] = sorted(set(cycle["motivos"]))
            invalid = set(cycle["motivos"]) - {"fronteira_entre_ambientes", "transicao_estimada_migracao"}
            complete = bool(work) and not invalid and all(r["horas_corridas"] is not None for r in work)
            cycle["duracao_completa"] = complete
            cycle["contem_estimativa"] = any(r["origem_duracao"] == "estimada_migracao" for r in members)
            cycle["contem_idade_aberta"] = any(r["origem_duracao"] == "idade_aberta_no_corte" for r in members)
            cycle["quantidade_passagens_operacionais"] = len(work)
            cycle["versao_calendario"] = calendar.version
            cycle["kpi_entrega_observada"] = (
                complete and cycle["situacao"] == "entregue"
                and all(r["origem_duracao"] == "observada" for r in members)
                and "fronteira_entre_ambientes" not in cycle["motivos"])
            for clock in ("horas_corridas", "horas_uteis"):
                cycle["operacao_" + clock] = round(sum(r[clock] for r in work), 3) if complete else None
                for cat in ("terceiros", "standby"):
                    selected = [r for r in members if r["categoria"] == cat]
                    cycle[cat + "_" + clock] = (round(sum(r[clock] for r in selected), 3)
                        if not invalid and all(r[clock] is not None for r in selected) else None)
            cycles.append(cycle)
    return {"rule": RULE, "cloud_modified": False, "passagens": passages,
            "ciclos": cycles, "excluidos": excluded}
