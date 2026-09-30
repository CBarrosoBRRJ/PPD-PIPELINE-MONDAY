"""Regressões da revisão de 30/09/2026: integridade das medidas, R1/R10/R26 e validação."""
from datetime import UTC, datetime

import monday_sla_orcamento.modelo_v19 as m
import pytest
from monday_sla_orcamento.talent_context import exclusion_reasons
from sls_orcamento_ppd.rules.business_time import BusinessCalendar

CAL = BusinessCalendar("America/Sao_Paulo")
CUT = datetime(2026, 9, 28, 3, tzinfo=UTC)


def at(day, hour=13):
    return datetime(2026, 9, day, hour, tzinfo=UTC)


def trajectory(pid, steps):
    rows = []
    for i, step in enumerate(steps):
        status, day = step[:2]
        conta = step[2] if len(step) > 2 else "globocorp"
        start = at(day)
        end = at(steps[i + 1][1]) if i + 1 < len(steps) else None
        rows.append({"interval_id": f"{pid}-{i}", "status_nome": status, "conta": conta,
                     "inicio": start, "saida": end, "fim": end, "origem": "observada" if end else "indisponivel",
                     "horas_uteis": round(CAL.hours(start, end), 3) if end else None,
                     "horas_corridas": round((end - start).total_seconds() / 3600, 3) if end else None})
    return rows


def attrs(name="[Marca] Talento"):
    return {"projeto_nome": name, "item_id_viu2": 7, "item_id_globocorp": 1, "contas": {"viu2", "globocorp"},
            "marca": "Marca", "talento": "Talento", "eh_interveniencia": False, "tipo_input": None,
            "tipo_projeto": None, "responsavel": "Ana", "nasceu_de_copia": False}


def one(out, table, pid):
    rows = [r for r in out[table] if r.get("projeto_id") == pid]
    assert len(rows) == 1
    return rows[0]


def test_feedback_continued_in_the_other_account_is_one_delivery():
    rows = trajectory("a", [("Entrada", 1, "viu2"), ("Em Elaboração", 2, "viu2"), ("Aguardando Feedback", 3, "viu2"),
                            ("Aguardando Feedback", 4, "globocorp"), ("Em revisão", 8, "globocorp"),
                            ("Aguardando Feedback", 9, "globocorp")])
    out = m.build({"a": rows}, {"a": attrs()}, cut=CUT, calendar=CAL)
    project = one(out, "monday_sla_projeto", "a")
    answers = [r for r in out["monday_sla_resposta_cliente"] if r["projeto_id"] == "a"]
    assert project["quantidade_entregas"] == 2 and project["quantidade_retrabalhos"] == 1
    assert [r["desfecho"] for r in answers] == ["pediu_ajuste", "aguardando"]
    # O tempo do cliente soma as duas contas (dia 3 → dia 8).
    assert answers[0]["horas_uteis"] == pytest.approx(rows[2]["horas_uteis"] + rows[3]["horas_uteis"])


def test_daily_series_never_shows_a_partial_total_as_complete():
    rows = trajectory("a", [("Entrada", 1), ("X", 2), ("Em Elaboração", 3), ("Aguardando Feedback", 4)])
    rows[1]["status_nome"] = None
    ats = attrs()
    ats["contas"] = {"globocorp"}
    out = m.build({"a": rows}, {"a": ats}, cut=CUT, calendar=CAL)
    assert one(out, "monday_sla_projeto", "a")["tempo_orcamento_horas_uteis"] is None
    days = [r for r in out["monday_sla_projeto_diario"] if r["projeto_id"] == "a" and r["data"] >= "2026-09-02"]
    assert days and all(r["tempo_orcamento_acumulado_horas_uteis"] is None for r in days)


def gold_row(item, order, status, start, end, **extra):
    return {"item_id": item, "ordem_etapa": order, "interval_id": f"{item}-{order}", "projeto_nome": "[Marca] Talento",
            "status_nome": status, "entrada_status_utc": start, "saida_status_utc": end,
            "qualidade_historico": "observed", "intervalo_aberto": end is None, **extra}


CONTEXT = {9: {"item_id": 9, "item_nome": "[Marca] Talento", "talentos_exclusivos_json": '["Talento"]',
               "interveniencia": "", "marca": "Marca"}}


def test_native_open_age_requires_the_same_evidence_as_the_consolidated_path():
    rows = [gold_row(9, 1, "Entrada", at(1).isoformat(), at(2).isoformat()),
            gold_row(9, 2, "Em Elaboração", at(2).isoformat(), None, status_atual_divergente=True)]
    passages, _, _ = m.native_globocorp(rows, set(), CONTEXT, CAL, CUT)
    last = next(iter(passages.values()))[-1]
    assert last["horas_uteis"] is None and last["origem"] == "indisponivel"
    rows[1]["status_atual_divergente"] = False
    passages, _, _ = m.native_globocorp(rows, set(), CONTEXT, CAL, CUT)
    assert next(iter(passages.values()))[-1]["origem"] == "idade_aberta_no_corte"


def test_native_undated_first_status_other_than_blank_or_entry_is_not_dropped():
    rows = [gold_row(9, 1, "Standby", None, None), gold_row(9, 2, "Entrada", at(1).isoformat(), at(2).isoformat()),
            gold_row(9, 3, "Em Elaboração", at(2).isoformat(), None, status_atual_divergente=False)]
    passages, _, excluded = m.native_globocorp(rows, set(), CONTEXT, CAL, CUT)
    assert passages == {} and next(iter(excluded.values()))["motivos"] == ["sem_entrada_inicial"]
    out = m.build({}, {}, cut=CUT, calendar=CAL, excluded=excluded)
    assert {r["situacao"] for r in out["monday_sla_cobertura"]} == {"sem_entrada"}


def test_blank_first_status_followed_by_entry_is_still_valid():
    rows = [gold_row(9, 1, None, None, None), gold_row(9, 2, "Entrada", at(1).isoformat(), at(2).isoformat())]
    passages, _, excluded = m.native_globocorp(rows, set(), CONTEXT, CAL, CUT)
    assert passages and not excluded


def test_validation_rejects_passage_linked_to_another_projects_cycle():
    a = trajectory("a", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)])
    b = trajectory("b", [("Entrada", 1), ("Em Elaboração", 2), ("Aguardando Feedback", 3)])
    out = m.build({"a": a, "b": b}, {"a": attrs(), "b": attrs()}, cut=CUT, calendar=CAL)
    cycle_b = one(out, "monday_sla_ciclo", "b")["ciclo_id"]
    row = next(r for r in out["monday_sla_passagem"] if r["projeto_id"] == "a" and r["ciclo_id"])
    row["ciclo_id"] = cycle_b
    with pytest.raises(ValueError, match="ciclo de outro projeto"):
        m.validate(out)


def test_held_items_keep_the_real_reason_in_coverage():
    held = [{"item_id": 9, "projeto_nome": "[Marca] Talento", "motivos": ["input_contexto_nao_verificado"]}]
    mapping = {"rows": []}
    context = [{"item_id": 9, "item_nome": "[Marca] Talento", "talentos_exclusivos_json": '["Talento"]', "interveniencia": ""}]
    out = m.from_pipeline([], [], {}, [], mapping, context, cut=CUT, calendar=CAL, held=held)
    reasons = {r["motivo"] for r in out["monday_sla_cobertura"]}
    assert reasons == {"input_contexto_nao_verificado"}


def test_empty_talent_list_text_is_not_a_crash():
    assert exclusion_reasons({"talentos_exclusivos_json": "", "interveniencia": "Maria"}) == []


def test_monday_token_only_goes_to_the_official_https_endpoint():
    from pydantic import ValidationError
    from sls_orcamento_ppd.config import Settings
    assert Settings(_env_file=None, monday_api_url="https://api.monday.com/v2").monday_api_url
    for url in ("http://api.monday.com/v2", "https://example.com/v2"):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, monday_api_url=url)
