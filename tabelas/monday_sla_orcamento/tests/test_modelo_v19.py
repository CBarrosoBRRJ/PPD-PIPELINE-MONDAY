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


def test_every_board_item_is_traceable(monkeypatch):
    # R15: item do quadro sem histórico de status e sem vínculo com a ViU2 entra na qualidade, com o motivo.
    rows = trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)])
    monkeypatch.setattr(m, "from_v18", lambda sla: ({"p": rows}, {"p": attrs()}))
    monkeypatch.setattr(m, "native_globocorp", lambda *a: ({}, {}, {}))
    context = [{"item_id": 1, "item_nome": "[Marca] Talento"}, {"item_id": 77, "item_nome": "Pedido novo"},
               {"item_id": 78, "item_nome": "Pedido sem talento", "talentos_exclusivos_json": "[]"},
               {"item_id": 79, "item_nome": "Pool", "talentos_exclusivos_json": '["Ana", "Bia"]'}]
    for c in context[1:]:
        c.setdefault("talentos_exclusivos_json", '["Ana"]')
    out = m.from_pipeline([], [], {}, [], {"rows": []}, context, cut=CUT, calendar=CAL)
    quality = {q["chave"]: q for q in out["monday_sla_qualidade"]}
    assert set(quality) == {"item:77", "item:78", "item:79"}
    assert quality["item:77"]["projeto_id"] is None and quality["item:77"]["situacao_calculo"] == "fora_do_calculo"
    assert json.loads(quality["item:77"]["motivos_json"]) == ["sem_historico_de_status"]
    # O motivo real da regra de talento aparece em vez de um motivo genérico.
    assert json.loads(quality["item:78"]["motivos_json"]) == ["talento_nao_informado"]
    assert json.loads(quality["item:79"]["motivos_json"]) == ["talento_multiplo"]
    assert quality["item:79"]["situacao_calculo"] == "fora_do_escopo"


# v20 (29/09/2026): pool, sem Entrada e catálogos

def test_pool_project_is_measured_apart_from_official_sla():
    rows = {"p": trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)]),
            "q": trajectory("q", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 4)])}
    ats = {pid: attrs() for pid in rows}
    ats["q"].update(projeto_nome="[Marca] Squad", pool=["talento_squad"], talentos=["Squad de talentos"])
    out = m.build(rows, ats, cut=CUT, calendar=CAL)
    assert [p["projeto_id"] for p in out["monday_sla_projeto"]] == ["p"]
    pool = one(out, "monday_sla_projeto_pool", "q")
    assert pool["motivo_pool"] == "talento_squad" and pool["tempo_orcamento_horas_uteis"] == 24.0
    assert not [r for r in out["monday_sla_passagem"] if r["projeto_id"] == "q"]
    assert json.loads(one(out, "monday_sla_qualidade", "q")["motivos_json"]) == ["talento_squad"]


def test_project_without_entry_keeps_full_trajectory_for_review():
    out = run(p=trajectory("p", [("Em Elaboração", 1), ("Aguardando Feedback", 2), ("Entrada", 3)]))
    row = one(out, "monday_sla_sem_entrada", "p")
    assert row["primeiro_status"] == "Em Elaboração" and row["passa_por_entrada_depois"] is True
    assert row["trajeto"] == "Em Elaboração → Aguardando Feedback → Entrada" and row["quantidade_entregas"] == 1
    assert [t["status"] for t in json.loads(row["trajeto_json"])] == ["Em Elaboração", "Aguardando Feedback", "Entrada"]
    assert out["monday_sla_projeto"] == []


def test_blank_then_entry_is_a_valid_start():
    out = run(p=trajectory("p", [(None, 1), ("Entrada", 2), ("Em Elaboração", 3), ("Aguardando Feedback", 4)]))
    assert out["monday_sla_sem_entrada"] == [] and len(out["monday_sla_projeto"]) == 1


def test_talent_and_brand_catalogs_group_spellings_and_flag_duplicates():
    rows = {"p": trajectory("p", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)])}
    context = [
        {"item_id": 1, "talentos_exclusivos_json": '["Jonas Sulzbach"]', "interveniencia": None, "marca": "Coca-Cola"},
        {"item_id": 2, "talentos_exclusivos_json": "[]", "interveniencia": "jonas  sulzbach", "marca": "coca-cola"},
        {"item_id": 3, "talentos_exclusivos_json": "[]", "interveniencia": "Jonas", "marca": "Coca Cola"},
        {"item_id": 4, "talentos_exclusivos_json": "[]", "interveniencia": "Ana, Bia", "marca": None},
    ]
    out = m.build(rows, {"p": attrs()}, cut=CUT, calendar=CAL, context=context)
    talents = {t["chave_talento"]: t for t in out["monday_dim_talento"]}
    assert set(talents) == {"jonas sulzbach", "jonas", "ana", "bia"}
    jonas = talents["jonas sulzbach"]
    assert jonas["quantidade_variantes"] == 2 and jonas["eh_exclusivo"] and jonas["usos_interveniencia"] == 1
    assert talents["jonas"]["possivel_duplicata_de"] == "jonas sulzbach"
    brands = {b["chave_marca"]: b for b in out["monday_dim_marca"]}
    assert set(brands) == {"coca cola"}  # grafias com hífen, caixa e espaço viram uma marca só
    assert brands["coca cola"]["itens_quadro"] == 3 and brands["coca cola"]["quantidade_variantes"] == 3
    # Pontes: o nome digitado em cada item ligado à chave do catálogo (relação no Power BI).
    ponte = {(r["item_id_globocorp"], r["chave_talento"]) for r in out["monday_ponte_talento"]}
    assert (2, "jonas sulzbach") in ponte and (4, "ana") in ponte and (4, "bia") in ponte
    assert {r["chave_marca"] for r in out["monday_ponte_marca"]} == {"coca cola"}


def test_coverage_counts_every_project_once_by_origin_and_situation():
    rows = {"ok": trajectory("ok", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)]),
            "se": trajectory("se", [("Em Elaboração", 1), ("Aguardando Feedback", 2)]),
            "pool": trajectory("pool", [("Entrada", 1), ("Aguardando Feedback", 2)])}
    ats = {pid: attrs() for pid in rows}
    ats["pool"].update(pool=["talento_multiplo"])
    ats["se"]["contas"] = {"viu2"}
    excluded = {"x": {"projeto_nome": "[Marca] Curadoria", "motivos": ["titulo_curadoria"], "contas": ["globocorp"]},
                "item:9": {"projeto_nome": "Sem talento", "item_id_globocorp": 9, "motivos": ["talento_nao_informado"]},
                "h": {"projeto_nome": "Antigo", "item_id_viu2": 5, "item_id_globocorp": 6, "motivos": ["titulo_fora_escopo"]}}
    out = m.build(rows, ats, cut=CUT, calendar=CAL, excluded=excluded)
    cov = {(r["origem"], r["situacao"]): r["itens"] for r in out["monday_sla_cobertura"]}
    assert cov == {("100% Globocorp", "analisado"): 1, ("100% ViU2", "sem_entrada"): 1,
                   ("100% Globocorp", "pool"): 1, ("100% Globocorp", "fora_do_escopo"): 1,
                   ("100% Globocorp", "erro_cadastro_talento"): 1,
                   ("ViU2 (histórico, ciclo não montado)", "fora_do_escopo"): 1}


def test_delivery_time_answers_how_long_until_first_delivery():
    out = run(a=trajectory("a", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)]),
              b=trajectory("b", [("Entrada", 1), ("Em Elaboração", 2), ("Standby", 3), ("Em Elaboração", 7),
                                 ("Aguardando Feedback", 9)]),
              c=trajectory("c", [("Entrada", 1), ("Em Elaboração", 2)]))
    a, b, c = (one(out, "monday_sla_tempo_entrega", pid) for pid in "abc")
    assert a["entregue"] and a["trabalho_horas_uteis"] == one(out, "monday_sla_projeto", "a")[
        "tempo_ate_primeira_entrega_horas_uteis"]
    assert a["dias_corridos"] == 2 and a["pausas_horas_uteis"] == 0
    assert b["pausas_horas_uteis"] > 0 and b["relogio_horas_uteis"] == pytest.approx(
        b["trabalho_horas_uteis"] + b["pausas_horas_uteis"])
    assert (a["percentil_na_fila"], a["faixa"], b["percentil_na_fila"], b["faixa"]) == (50.0, "ate_mediana", 100.0, "cauda")
    assert not c["entregue"] and c["trabalho_horas_uteis"] is None and c["faixa"] is None and c["eh_atipico"] is None
