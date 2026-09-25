import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from monday_sla_orcamento.cycle_contract import project as contract
from monday_sla_orcamento.live_cycles import build
from sls_orcamento_ppd.rules.business_time import BusinessCalendar

CAL = BusinessCalendar("America/Sao_Paulo")


def test_open_age_uses_verified_source_cut_and_rejects_divergence():
    data = rows(['Entrada'])
    row = data[0]
    row.pop('estado_confirmado_no_corte')
    row.update(interval_id_origem='native', item_id_globocorp=123)
    source = {'qualidade_historico': 'observed', 'intervalo_aberto': True,
        'eh_ultimo_registro': True, 'status_atual_divergente': False,
        'tempo_status_atual_horas': 10, 'versao_calendario': CAL.version,
        'interval_id': 'native', 'item_id': 123, 'saida_status_utc': None,
        'corte_utc': '2026-09-24T23:00:00Z',
        'entrada_status_utc': row['entrada_status_utc'], 'status_nome': 'Entrada'}
    row['registro_origem_json'] = json.dumps(source)
    assert run(data)['ciclos'][0]['operacao_horas_corridas'] == 10
    for key, invalid in [('status_atual_divergente', True), ('corte_utc', '2026-09-25T23:00:00Z'),
                         ('interval_id', 'wrong'), ('qualidade_historico', 'initial_inferred')]:
        row['registro_origem_json'] = json.dumps({**source, key: invalid})
        assert run(data)['ciclos'][0]['operacao_horas_corridas'] is None


def rows(labels):
    start = datetime(2026, 9, 24, 13, tzinfo=UTC)
    return [{"projeto_id": "p", "interval_id": str(i), "status_nome": label,
             "ambiente_origem": "globocorp", "entrada_status_utc": (start + timedelta(hours=i)).isoformat(),
             "saida_status_utc": (start + timedelta(hours=i + 1)).isoformat() if i < len(labels)-1 else None,
             "elegivel_comparacao": i < len(labels)-1,
             "versao_calendario_origem": CAL.version,
             "registro_origem_json": '{"qualidade_historico":"observed"}',
             "estado_confirmado_no_corte": True} for i, label in enumerate(labels)]


def run(data):
    return build(data, CAL, cut="2026-09-24T23:00:00Z")


def test_revisions_open_new_cycle_without_entry_and_keep_returns():
    data = rows(["Entrada", "Em Elaboração", "Aguardando Feedback", "Em revisão",
                 "Em Elaboração", "Em revisão", "Aguardando Feedback"])
    before = deepcopy(data)
    result = run(data)
    assert data == before
    assert len(result["ciclos"]) == 2
    assert [c["operacao_horas_corridas"] for c in result["ciclos"]] == [2, 3]
    assert all(c["kpi_entrega_observada"] for c in result["ciclos"])


def test_entry_queue_and_work_in_progress():
    result = run(rows(["Entrada", "Em Elaboração"]))
    cycle = result["ciclos"][0]
    assert cycle["situacao"] == "em_andamento"
    assert cycle["operacao_horas_corridas"] == 10
    assert not cycle["kpi_entrega_observada"]
    assert run(rows(["Entrada"]))["ciclos"][0]["operacao_horas_corridas"] == 10


def test_current_snapshot_not_enough_for_open_age():
    data = rows(["Entrada"])
    data[0].pop("estado_confirmado_no_corte")
    assert run(data)["ciclos"][0]["operacao_horas_corridas"] is None


def test_pauses_separate_and_do_not_restart_cycle():
    result = run(rows(["Entrada", "Em elaboração - Retorno Marca/Executivo",
                       "Standby", "Em revisão", "Aguardando Feedback"]))
    assert len(result["ciclos"]) == 1
    assert result["ciclos"][0]["operacao_horas_corridas"] == 2
    assert [p["categoria"] for p in result["passagens"]] == [
        "operacao", "terceiros", "standby", "operacao", "feedback"]


def test_null_prefix_allowed_missing_entry_excluded():
    result = run(rows([None, "Entrada", "Em revisão", "Aguardando Feedback"]))
    assert result["passagens"][0]["origem_duracao"] == "prefixo_nulo"
    assert result["ciclos"][0]["operacao_horas_corridas"] == 2
    assert run(rows(["Em revisão", "Entrada"]))["excluidos"]


def test_migration_preserves_cycle_but_never_certifies_gap():
    data = rows(["Entrada", "Em revisão", "Aguardando Feedback"])
    for row in data[:2]:
        row["ambiente_origem"] = "viu2"
    data[1]["saida_status_utc"] = None
    data[1]["elegivel_comparacao"] = False
    cycle = run(data)["ciclos"][0]
    assert cycle["situacao"] == "entregue"
    assert cycle["operacao_horas_corridas"] is None
    assert not cycle["kpi_entrega_observada"]


def test_post_delivery_gap_does_not_erase_observed_cycle():
    data = rows(["Entrada", "Em revisão", "Aguardando Feedback", "Encerrado"])
    data[2]["saida_status_utc"] = None
    data[3]["ambiente_origem"] = "viu2"
    assert run(data)["ciclos"][0]["kpi_entrega_observada"]


def test_stable_cycle_key_as_it_closes():
    opened = run(rows(["Entrada", "Em revisão"]))["ciclos"][0]
    closed = run(rows(["Entrada", "Em revisão", "Aguardando Feedback"]))["ciclos"][0]
    assert opened["ciclo_id"] == closed["ciclo_id"]


@pytest.mark.parametrize("label", ["Novo status", None])
def test_unknown_inside_cycle_blocks_total(label):
    assert run(rows(["Entrada", label, "Aguardando Feedback"]))["ciclos"][0]["operacao_horas_corridas"] is None


def test_unverified_feedback_does_not_approve():
    data = rows(["Entrada", "Aguardando Feedback"])
    data[-1]["registro_origem_json"] = '{}'
    assert not run(data)["ciclos"][0]["kpi_entrega_observada"]


def test_duplicate_rejected():
    data = rows(["Entrada"])
    with pytest.raises(ValueError):
        run(data + data)


def migration(labels):
    data = rows(labels)
    for i, row in enumerate(data):
        row.update(item_id_viu2=1, item_id_globocorp=2,
                   qualidade_identidade='selected_by_user_accepted_policy')
        if i < 2:
            row['ambiente_origem'] = 'viu2'
            row['registro_origem_json'] = '{"qualidade_rotulo":"label_observed_at_start"}'
    data[1]['saida_status_utc'] = None
    data[1]['elegivel_comparacao'] = False
    return data


def test_estimated_migration_delivers_analysis_not_observed_kpi():
    result = run(migration(['Entrada', 'Em revisão', 'Aguardando Feedback']))
    cycle = contract(result)[0]
    assert cycle['contem_estimativa']
    assert cycle['operacao_horas_corridas'] == 2
    assert not cycle['kpi_entrega_observada']
    assert result['passagens'][1]['saida_observada_utc'] is None
    assert result['passagens'][1]['saida_estimada_utc'] is not None


def test_same_status_continues_without_return_or_new_cycle():
    result = run(migration(['Entrada', 'Em revisão', 'Em revisão', 'Aguardando Feedback']))
    assert len(result['ciclos']) == 1
    a, b = result['passagens'][1:3]
    assert b['eh_continuacao_mesmo_status']
    assert not b['eh_retorno_status']
    assert a['grupo_permanencia_id'] == b['grupo_permanencia_id']
    assert contract(result)[0]['operacao_horas_corridas'] == 3


def test_missing_identity_does_not_estimate():
    data = migration(['Entrada', 'Em revisão', 'Aguardando Feedback'])
    data[2]['item_id_globocorp'] = 3
    assert not run(data)['ciclos'][0]['contem_estimativa']


def test_contract_rejects_orphan_and_corrupt_kpi():
    result = run(rows(['Entrada', 'Aguardando Feedback']))
    contract(result)
    result['ciclos'][0]['interval_id_inicio'] = 'missing'
    with pytest.raises(ValueError):
        contract(result)
    result = run(migration(['Entrada', 'Em revisão', 'Aguardando Feedback']))
    result['ciclos'][0]['kpi_entrega_observada'] = True
    with pytest.raises(ValueError):
        contract(result)
