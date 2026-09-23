from copy import deepcopy

import pytest
from monday_sla_orcamento.consolidation import build


def inputs():
    old = {"item_id": 1, "board_id": 18393336134, "interval_id": "old1", "status_index": "7",
           "entrada_status_utc": "2026-09-01T10:00:00Z", "saida_status_utc": "2026-09-01T11:00:00Z",
           "entrada_status_local": "2026-09-01T07:00:00", "saida_status_local": "2026-09-01T08:00:00",
           "ordem_etapa": 1, "projeto_nome": "Projeto", "status_nome": "Entrada",
           "duracao_horas": 1.0, "duracao_horas_uteis": 0.0, "marca_original": "Marca",
           "talento_original": None, "retorno_observado": False, "pendencias_json": "[]",
           "situacao_passagem": "observed_closed_candidate", "cadastro_referencia_utc": None,
           "versao_calendario": "test"}
    new = {"item_id": 2, "board_id": 18429499488, "interval_id": "new1", "status_id": "18429499488:status_19:8",
           "entrada_status_utc": "2026-09-04T10:00:00Z", "saida_status_utc": None,
           "entrada_status_local": "2026-09-04T07:00:00", "saida_status_local": None,
           "ordem_etapa": 1, "projeto_nome": "Projeto novo", "status_nome": "Encerrado",
           "duracao_horas": 24.0, "duracao_horas_uteis": 8.0, "marca_nome": "Marca tratada",
           "talento_nome": None, "responsavel_orcamento": "Pessoa", "eh_retorno": False,
           "qualidade_historico": "observed", "cadastro_referencia_utc": None,
           "versao_calendario": "test", "corte_utc": "2026-09-05T10:00:00Z"}
    pair = {"projeto_id": "9af3d7b3-ed00-4ad8-8fef-7e21f4f0b771", "viu2_item_id": "1", "globocorp_item_id": "2",
            "viu2_account_id": "5890468", "viu2_board_id": "18393336134",
            "globocorp_account_id": "21453629", "globocorp_board_id": "18429499488",
            "identity_quality": "selected_by_user_accepted_policy"}
    return [old], [new], {"version": "selected-identity-v1", "rows": [pair]}


def test_no_cross_source_fabrication_or_source_mutation():
    old, new, mapping = inputs()
    original = deepcopy((old, new, mapping))
    rows, report = build(old, new, mapping)
    assert (old, new, mapping) == original
    assert report["projects"] == 1
    assert [r["ordem_etapa"] for r in rows] == [1, 2]
    assert rows[0]["marca_nome"] is None and rows[0]["responsavel_orcamento"] is None
    assert rows[1]["duracao_horas"] is None  # No source open-to-cut metric as closed SLA.
    assert all(r["eh_retorno"] is None and not r["elegivel_comparacao"] for r in rows)


def test_missing_historical_input_excludes_entire_pair_not_confirmed_blank():
    old, new, mapping = inputs()
    assert build(old, new, mapping, old_inputs={})[0] == []
    assert len(build(old, new, mapping, old_inputs={(18393336134, 1): None})[0]) == 2
    assert build(old, new, mapping, old_inputs={(18393336134, 1): "Proativo"})[0] == []


@pytest.mark.parametrize("origin", [0, 1])
def test_title_exclusion_removes_both_sides_of_selected_project(origin):
    old, new, mapping = inputs()
    (old, new)[origin][0]["projeto_nome"] = "[Levop] Interno"
    rows, report = build(old, new, mapping)
    assert rows == []
    assert report["title_excluded_selected_projects"] == 1


def test_unknown_start_not_given_a_chronological_order():
    old, new, mapping = inputs()
    new[0].update(entrada_status_utc=None, entrada_status_local=None,
                  saida_status_utc="2026-09-04T10:00:00Z", qualidade_historico="initial_inferred")
    rows, report = build(old, new, mapping)
    assert len(rows) == 1 and rows[0]["ambiente_origem"] == "viu2"
    assert report["excluded_source_rows"]["globocorp:sem_entrada_comprovada"] == 1


def test_overlapping_durations_blocked():
    old, new, mapping = inputs()
    old[0]["saida_status_utc"] = "2026-09-05T12:00:00Z"
    rows, report = build(old, new, mapping)
    assert report["overlapping_rows"] == 2
    assert all(r["duracao_horas"] is None for r in rows)


def test_unmatched_not_invented_and_missing_gold_not_reintroduced():
    old, new, mapping = inputs()
    new[0]["item_id"] = 3
    rows, report = build(old, new, mapping)
    assert rows == []
    assert report["excluded_source_rows"] == {"viu2:sem_item_na_gold_atual": 1, "globocorp:sem_mapa": 1}


@pytest.mark.parametrize("fault", ["duplicate", "board", "status", "cutoff", "map_duplicate"])
def test_invalid_inputs_fail_closed(fault):
    old, new, mapping = inputs()
    if fault == "duplicate":
        old.append(deepcopy(old[0]))
    elif fault == "board":
        new[0]["board_id"] = 999
    elif fault == "status":
        new[0]["status_id"] = "invalid"
    elif fault == "cutoff":
        extra = deepcopy(new[0])
        extra["corte_utc"] = "2026-09-06T10:00:00Z"
        new.append(extra)
    else:
        mapping["rows"].append(deepcopy(mapping["rows"][0]))
    with pytest.raises(ValueError):
        build(old, new, mapping)


def test_tied_timestamps_quarantine_project_instead_of_inventing_order():
    old, new, mapping = inputs()
    new[0]["entrada_status_utc"] = old[0]["entrada_status_utc"]
    rows, report = build(old, new, mapping)
    assert not rows
    assert report["excluded_source_rows"]["consolidado:projeto_com_ordem_ambigua"] == 2


@pytest.mark.parametrize("terminal", ["Encerrado", "Declinado pelo Mercado", "Declinado Internamente"])
def test_terminal_without_exit_closes_at_entry_without_accumulation(terminal):
    old, new, mapping = inputs()
    new[0]["status_nome"] = terminal
    rows, _ = build(old, new, mapping)
    last = rows[-1]
    assert last["status_terminal"] is True
    assert last["finalizacao_observada_utc"] == last["entrada_status_utc"]
    assert last["saida_status_utc"] is None and last["duracao_horas"] is None
    assert last["tempo_ciclo_observado_horas"] is None  # No cross-account total invented.


def test_closed_source_cycle_and_reopening_preserve_previous_close():
    old, new, mapping = inputs()
    closed = deepcopy(old[0])
    closed.update(interval_id="old2", ordem_etapa=2, status_nome="Encerrado", status_index="8",
                  entrada_status_utc="2026-09-01T11:00:00Z", saida_status_utc="2026-09-01T12:00:00Z")
    reopened = deepcopy(old[0])
    reopened.update(interval_id="old3", ordem_etapa=3,
                    entrada_status_utc="2026-09-01T12:00:00Z", saida_status_utc="2026-09-01T13:00:00Z")
    again = deepcopy(closed)
    again.update(interval_id="old4", ordem_etapa=4, entrada_status_utc="2026-09-01T13:00:00Z",
                 saida_status_utc=None, duracao_horas=None, duracao_horas_uteis=None)
    rows, _ = build([old[0], closed, reopened, again], new, mapping)
    historical = [r for r in rows if r["ambiente_origem"] == "viu2"]
    assert [r["ciclo_observado_origem"] for r in historical] == [1, 1, 2, 2]
    assert historical[2]["reabertura_comprovada_origem"] is True
    assert historical[1]["tempo_ciclo_observado_horas"] == 1.0
    assert historical[3]["tempo_ciclo_observado_horas"] == 1.0
    assert historical[1]["duracao_horas"] is None


def test_gap_blocks_cycle_total_and_unknown_terminal_stays_unknown():
    old, new, mapping = inputs()
    gap = deepcopy(old[0])
    gap.update(interval_id="old2", ordem_etapa=2, status_nome="Encerrado", status_index="8",
               entrada_status_utc="2026-09-01T15:00:00Z", saida_status_utc=None,
               duracao_horas=None, duracao_horas_uteis=None)
    new[0]["status_nome"] = None
    rows, _ = build([old[0], gap], new, mapping)
    assert rows[1]["tempo_ciclo_observado_horas"] is None
    assert rows[-1]["status_terminal"] is None
    assert rows[-1]["finalizacao_observada_utc"] is None


def test_future_closed_deal_requires_explicit_configuration():
    old, new, mapping = inputs()
    new[0]["status_nome"] = "Negócio Fechado"
    rows, _ = build(old, new, mapping)
    assert rows[-1]["status_terminal"] is False
    rows, _ = build(old, new, mapping, terminal_labels=("Negócio Fechado",))
    assert rows[-1]["status_terminal"] is True
