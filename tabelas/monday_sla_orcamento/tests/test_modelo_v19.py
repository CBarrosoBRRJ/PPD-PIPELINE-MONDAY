import json
from datetime import UTC, datetime

import monday_sla_orcamento.modelo_v19 as m
import pytest
from sls_orcamento_ppd.rules.business_time import BusinessCalendar

CAL = BusinessCalendar("America/Sao_Paulo")
CUT = datetime(2026, 9, 28, 3, tzinfo=UTC)


def at(day, hour=13):  # 13h UTC = 10h em São Paulo
    return datetime(2026, 9, day, hour, tzinfo=UTC)


def trajectory(pid, steps, origin="observada"):
    """steps: (status, dia início); cada passagem termina no início da próxima."""
    rows = []
    for i, (status, day) in enumerate(steps):
        start = at(day)
        end = at(steps[i + 1][1]) if i + 1 < len(steps) else None
        rows.append({"interval_id": f"{pid}-{i}", "status_nome": status, "conta": "globocorp",
                     "inicio": start, "saida": end, "fim": end, "origem": origin if end else "indisponivel",
                     "horas_uteis": round(CAL.hours(start, end), 3) if end else None,
                     "horas_corridas": round((end - start).total_seconds() / 3600, 3) if end else None})
    return rows


def attrs(name="[Marca] Talento"):
    return {"projeto_nome": name, "item_id_viu2": None, "item_id_globocorp": 1, "contas": {"globocorp"},
            "marca": "Marca", "talento": "Talento", "eh_interveniencia": False, "tipo_input": None,
            "tipo_projeto": None, "responsavel": "Ana", "nasceu_de_copia": False}


def run(**projects):
    passages = {pid: rows for pid, rows in projects.items()}
    return m.build(passages, {pid: attrs(pid) for pid in projects}, cut=CUT, calendar=CAL)


def one(out, table, pid):
    rows = [r for r in out[table] if r.get("projeto_id") == pid]
    assert len(rows) == 1
    return rows[0]


def test_simple_delivery_and_automatic_close_is_not_client_answer():
    rows = trajectory("p", [("Entrada", 1), ("Em Elaboração - Orçamentos", 2), ("Aguardando Feedback", 3)])
    rows.append({**rows[-1], "interval_id": "p-x", "status_nome": "Encerrado", "inicio": datetime(2026, 10, 2, 13, tzinfo=UTC)})
    rows[-2].update(fim=rows[-1]["inicio"], saida=rows[-1]["inicio"], origem="observada",
                    horas_uteis=round(CAL.hours(at(3), rows[-1]["inicio"]), 3))
    out = m.build({"p": rows}, {"p": attrs()}, cut=datetime(2026, 10, 3, tzinfo=UTC), calendar=CAL)
    project = one(out, "monday_sla_projeto", "p")
    assert project["situacao_atual"] == "encerrado_automatico"
    assert project["tempo_orcamento_horas_uteis"] == 16.0  # 2 dias úteis de 8h
    answer = one(out, "monday_sla_resposta_cliente", "p")
    assert answer["desfecho"] == "encerrado_automatico" and answer["conta_como_resposta"] is False
    assert project["resposta_cliente_horas_uteis"] is None
    assert {e["tipo_erro"] for e in out["monday_sla_erro_preenchimento"]} == {"resposta_nao_registrada"}


def test_rework_opens_new_cycle_and_sums_time():
    rows = trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3),
                            ("Em revisão", 4), ("Aguardando Feedback", 7), ("Declinado pelo Mercado", 8)])
    out = run(p=rows)
    project = one(out, "monday_sla_projeto", "p")
    cycles = sorted(out["monday_sla_ciclo"], key=lambda c: c["numero_ciclo"])
    assert [c["tipo_ciclo"] for c in cycles] == ["orcamento", "retrabalho"]
    assert project["quantidade_entregas"] == 2 and project["quantidade_retrabalhos"] == 1
    assert project["tempo_orcamento_horas_uteis"] == cycles[0]["trabalho_horas_uteis"] + cycles[1]["trabalho_horas_uteis"]
    outcomes = [r["desfecho"] for r in sorted(out["monday_sla_resposta_cliente"], key=lambda r: r["numero_entrega"])]
    assert outcomes == ["pediu_ajuste", "decidiu_declinado"]
    assert project["situacao_atual"] == "cliente_decidiu"


def test_standby_and_brand_wait_do_not_count():
    rows = trajectory("p", [("Entrada", 1), ("Standby", 2), ("Em elaboração - Retorno Marca/Executivo", 3),
                            ("Em Elaboração", 4), ("Aguardando Feedback", 7)])
    out = run(p=rows)
    project = one(out, "monday_sla_projeto", "p")
    assert project["tempo_orcamento_horas_uteis"] == 16.0  # Entrada (8h) + Em Elaboração (dia 4, sexta: 8h)
    assert project["standby_horas_uteis"] == 8.0 and project["espera_marca_horas_uteis"] == 8.0


def test_delivery_without_entry_is_error_and_out_of_calculation():
    out = run(p=trajectory("p", [("Aguardando Feedback", 1), ("Encerrado", 2)]))
    assert not out["monday_sla_projeto"]
    quality = one(out, "monday_sla_qualidade", "p")
    assert quality["situacao_calculo"] == "fora_do_calculo"
    assert json.loads(quality["motivos_json"]) == ["sem_entrada_inicial"]
    assert [e["tipo_erro"] for e in out["monday_sla_erro_preenchimento"]] == ["inicio_sem_entrada"]


def test_terminal_in_the_middle_is_ignored_and_reported():
    rows = trajectory("p", [("Entrada", 1), ("Declinado Internamente", 2), ("Em revisão", 3), ("Aguardando Feedback", 4)])
    out = run(p=rows)
    project = one(out, "monday_sla_projeto", "p")
    assert project["situacao_atual"] == "aguardando_cliente" and project["quantidade_entregas"] == 1
    ignored = [p for p in out["monday_sla_passagem"] if p["ignorada"]]
    assert [p["motivo_ignorada"] for p in ignored] == ["terminal_no_meio"]
    assert "terminal_no_meio" in {e["tipo_erro"] for e in out["monday_sla_erro_preenchimento"]}


def test_unknown_duration_never_becomes_zero():
    rows = trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)])
    rows[1].update(horas_uteis=None, horas_corridas=None, origem="indisponivel")
    project = one(run(p=rows), "monday_sla_projeto", "p")
    assert project["tempo_orcamento_horas_uteis"] is None and project["completo"] is False


def test_open_project_gets_alert_from_status_reference(monkeypatch):
    monkeypatch.setattr(m, "REFERENCE_MIN_SAMPLES", 2)
    done = {f"d{i}": trajectory(f"d{i}", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)])
            for i in range(3)}
    late = trajectory("late", [("Entrada", 1), ("Em Elaboração", 2)])
    out = run(**done, late=late)
    row = one(out, "monday_sla_em_andamento", "late")
    assert row["situacao_atual"] == "em_orcamento"
    assert row["nivel_alerta"] == "critico"  # 17 dias úteis contra referência de 8h
    kpi = {k["mes"]: k for k in out["monday_sla_kpi_mensal"]}["2026-09-01"]
    assert kpi["projetos_iniciados"] == 4 and kpi["projetos_primeira_entrega"] == 3


def test_contract_rejects_orphans():
    out = run(p=trajectory("p", [("Entrada", 1), ("Aguardando Feedback", 2)]))
    out["monday_sla_ciclo"][0]["projeto_id"] = "outro"
    with pytest.raises(ValueError, match="órfão"):
        m.validate(out)


def test_daily_series_accumulates_only_budget_time():
    rows = trajectory("p", [("Entrada", 1), ("Standby", 2), ("Em Elaboração", 3), ("Aguardando Feedback", 4)])
    daily = {d["data"]: d for d in run(p=rows)["monday_sla_projeto_diario"] if d["projeto_id"] == "p"}
    # Aguardando cliente segue aberto: a série vai até o corte.
    assert min(daily) == "2026-09-01" and max(daily) == "2026-09-27"
    assert daily["2026-09-02"]["tempo_orcamento_acumulado_horas_uteis"] == 8.0  # Standby não soma
    assert daily["2026-09-04"]["tempo_orcamento_acumulado_horas_uteis"] == 16.0
    assert daily["2026-09-04"]["entregas_ate_o_dia"] == 1


def test_duplicated_item_is_studied_apart_from_sla():
    original = trajectory("orig", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)])
    copy_rows = trajectory("copia", [("Entrada", 8), ("Em Elaboração", 9), ("Aguardando Feedback", 10)])
    attributes = {"orig": attrs("[Marca] Talento"),
                  "copia": {**attrs("[Marca] Talento (novo escopo)"), "nasceu_de_copia": True,
                            "status_copiado": "Aguardando Feedback"}}
    out = m.build({"orig": original, "copia": copy_rows}, attributes, cut=CUT, calendar=CAL)
    assert [p["projeto_id"] for p in out["monday_sla_projeto"]] == ["orig"]
    duplicate = one(out, "monday_sla_item_duplicado", "copia")
    assert duplicate["projeto_relacionado"] == "orig" and duplicate["quantidade_entregas"] == 1
    assert json.loads(one(out, "monday_sla_qualidade", "copia")["motivos_json"]) == ["item_duplicado"]


def test_standby_has_own_table_and_leaves_open_queue():
    parked = trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Standby", 3)])
    resumed = trajectory("r", [("Entrada", 1), ("Standby", 2), ("Em Elaboração", 3), ("Aguardando Feedback", 4)])
    out = run(p=parked, r=resumed)
    row = one(out, "monday_sla_standby", "p")
    assert row["status_anterior"] == "Em Elaboração" and row["dias_corridos_parado"] == 25
    assert not [r for r in out["monday_sla_em_andamento"] if r["projeto_id"] == "p"]
    assert not [r for r in out["monday_sla_standby"] if r["projeto_id"] == "r"]
    assert one(out, "monday_sla_projeto", "r")["tempo_orcamento_horas_uteis"] == 16.0  # Standby não conta


def test_proposed_statuses_are_recognized():
    won = trajectory("w", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3),
                           ("Aprovado – negócio fechado", 4)])
    silent = trajectory("s", [("Entrada", 1), ("Aguardando Feedback", 2), ("Sem retorno do cliente", 7)])
    counter = trajectory("c", [("Entrada", 1), ("Aguardando Feedback", 2), ("Contraproposta", 3),
                               ("Aguardando Feedback", 4)])
    out = run(w=won, s=silent, c=counter)
    assert one(out, "monday_sla_projeto", "w")["situacao_atual"] == "negocio_fechado"
    answer = one(out, "monday_sla_resposta_cliente", "s")
    assert answer["desfecho"] == "sem_retorno_cliente" and answer["conta_como_resposta"] is False
    assert one(out, "monday_sla_projeto", "c")["quantidade_retrabalhos"] == 1


def test_status_usage_counts_every_source_passage():
    usage = m.status_usage([
        {"status_nome": "Entrada", "entrada_status_utc": "2026-09-01T13:00:00+00:00", "board_id": 1, "item_id": 1},
        {"status_nome": "Entrada", "entrada_status_utc": "2025-01-01T13:00:00+00:00", "board_id": 1, "item_id": 2},
        {"status_nome": "Standby", "entrada_status_utc": None, "board_id": 1, "item_id": 3}])
    out = m.build({"p": trajectory("p", [("Entrada", 1), ("Aguardando Feedback", 2)])}, {"p": attrs()},
                  cut=CUT, calendar=CAL, usage=usage, board_labels=["Entrada", "Em revisão (Planejamento)"])
    dims = {d["status_nome"]: d for d in out["monday_dim_status"]}
    assert (dims["Entrada"]["passagens_total"], dims["Entrada"]["passagens_ano_atual"], dims["Entrada"]["itens_total"]) == (2, 1, 2)
    assert dims["Em revisão (Planejamento)"]["passagens_total"] == 0 and dims["Em revisão (Planejamento)"]["no_quadro_atual"]


# Revisão técnica de 28/09/2026 (docs/REVISAO_TECNICA_V19_2026_09_28.md)

def test_pause_after_delivery_is_not_rework_nor_adjustment():
    out = run(p=trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3), ("Standby", 4)]))
    project = one(out, "monday_sla_projeto", "p")
    answer = one(out, "monday_sla_resposta_cliente", "p")
    assert project["quantidade_retrabalhos"] == 0 and len(out["monday_sla_ciclo"]) == 1
    assert answer["desfecho"] == "pausado" and answer["conta_como_resposta"] is False
    assert out["monday_sla_standby"][0]["projeto_id"] == "p"  # a pausa segue na tabela de Standby


def test_brand_wait_after_delivery_then_work_is_one_rework():
    out = run(p=trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3),
                                 ("Em elaboração - Retorno Marca/Executivo", 4), ("Em Revisão", 7),
                                 ("Aguardando Feedback", 8)]))
    project = one(out, "monday_sla_projeto", "p")
    first = next(r for r in out["monday_sla_resposta_cliente"] if r["numero_entrega"] == 1)
    assert project["quantidade_retrabalhos"] == 1 and project["espera_marca_horas_uteis"] == 8.0  # sex 04/09; 07/09 é feriado
    assert first["desfecho"] == "pediu_ajuste" and first["status_seguinte"] == "Em Revisão"
    rework = next(c for c in out["monday_sla_ciclo"] if c["tipo_ciclo"] == "retrabalho")
    assert rework["inicio_utc"] == m.iso(at(7)) and not rework["espera_marca_horas_uteis"]


def test_midnight_event_belongs_to_next_day():
    rows = trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)])
    rows[2]["inicio"] = datetime(2026, 9, 3, 3, tzinfo=UTC)  # 00:00 em São Paulo
    rows[1].update(saida=rows[2]["inicio"], fim=rows[2]["inicio"],
                   horas_uteis=CAL.hours(rows[1]["inicio"], rows[2]["inicio"]))
    out = run(p=rows)
    day = next(r for r in out["monday_sla_projeto_diario"] if r["data"] == "2026-09-02")
    assert (day["status_fim_do_dia"], day["entregas_ate_o_dia"]) == ("Em Elaboração", 0)


def test_daily_series_keeps_standby_days_until_cut():
    out = run(p=trajectory("p", [("Entrada", 1), ("Standby", 2)]))
    days = out["monday_sla_projeto_diario"]
    assert days[-1]["data"] == "2026-09-27" and days[-1]["situacao_no_dia"] == "parado_standby"
    assert days[-1]["tempo_orcamento_acumulado_horas_uteis"] == days[1]["tempo_orcamento_acumulado_horas_uteis"]


def test_closed_project_series_ends_on_closing_day():
    out = run(p=trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Declinado pelo Mercado", 4)]))
    days = out["monday_sla_projeto_diario"]
    assert days[-1]["data"] == "2026-09-04" and days[-1]["status_fim_do_dia"] == "Declinado pelo Mercado"


def test_duplicate_links_only_a_single_eligible_original():
    def case(originals):
        pids = originals + ["copia"]
        rows = {pid: trajectory(pid, [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)]) for pid in pids}
        ats = {pid: {**attrs("[Marca] Talento"), "item_id_globocorp": i} for i, pid in enumerate(pids, 1)}
        ats["copia"].update(projeto_nome="[Marca] Talento [novo escopo]", nasceu_de_copia=True)
        return m.build(rows, ats, cut=CUT, calendar=CAL)
    single = case(["original"])
    assert one(single, "monday_sla_item_duplicado", "copia")["projeto_relacionado"] == "original"
    ambiguous = case(["original-a", "original-b"])
    assert one(ambiguous, "monday_sla_item_duplicado", "copia")["projeto_relacionado"] is None
    assert "duplicado_original_ambiguo" in {e["tipo_erro"] for e in ambiguous["monday_sla_erro_preenchimento"]}


def test_validation_rejects_negative_duration_and_mixed_cuts():
    out = run(p=trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)]))
    bad = json.loads(json.dumps(out))
    bad["monday_sla_passagem"][0]["horas_uteis"] = -1.0
    with pytest.raises(ValueError, match="negativo"):
        m.validate(bad)
    bad = json.loads(json.dumps(out))
    bad["monday_sla_ciclo"][0]["corte_utc"] = "2026-09-27T03:00:00.000000+00:00"
    with pytest.raises(ValueError, match="mais de um corte"):
        m.validate(bad)
    bad = json.loads(json.dumps(out))
    bad["monday_sla_projeto"][0]["quantidade_retrabalhos"] = 1
    with pytest.raises(ValueError, match="retrabalhos"):
        m.validate(bad)
