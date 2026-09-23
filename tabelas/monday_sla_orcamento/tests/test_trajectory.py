from copy import deepcopy

import pytest
from monday_sla_orcamento.trajectory import audit


def rows():
    base = dict(projeto_id="p", item_id_viu2=1, item_id_globocorp=2,
                ambiente_origem="viu2", item_id=1, status_terminal=False)
    return [dict(base, ordem_etapa=1, status_nome="Entrada",
                 entrada_status_utc="2026-09-01T10:00:00Z", saida_status_utc=None),
            dict(base, ordem_etapa=2, status_nome="Encerrado", ambiente_origem="globocorp",
                 item_id=2, status_terminal=True,
                 entrada_status_utc="2026-09-02T10:00:00Z", saida_status_utc=None)]


def test_gap_preserved_no_inferred_total_or_mutation():
    data = rows()
    before = deepcopy(data)
    report = audit(data)
    assert data == before
    assert not report["total_sla_approved"]
    assert report["projects_by_reason"]["transicao_sem_continuidade_temporal"] == 1
    assert report["projects_by_reason"]["fronteira_entre_ambientes_nao_comprovada"] == 1


@pytest.mark.parametrize("fault", ["order", "identity", "time", "native_id", "end"])
def test_structural_fault_blocks(fault):
    data = rows()
    field, value = {"order": ("ordem_etapa", 1), "identity": ("item_id_viu2", 5),
                    "time": ("entrada_status_utc", "2026-08-01T10:00:00Z"),
                    "native_id": ("item_id", 99),
                    "end": ("saida_status_utc", "2026-08-01T10:00:00Z")}[fault]
    data[1][field] = value
    with pytest.raises(ValueError):
        audit(data)


def test_terminal_only_not_complete():
    data = rows()[1:]
    data[0]["ordem_etapa"] = 1
    report = audit(data)
    assert report["terminal_only_projects"] == 1
    assert "passagem_unica" in report["details"][0]["motivos"]


def test_connected_times_do_not_prove_migration():
    data = rows()
    data[0]["saida_status_utc"] = data[1]["entrada_status_utc"]
    report = audit(data)
    assert "transicao_sem_continuidade_temporal" not in report["projects_by_reason"]
    assert "fronteira_entre_ambientes_nao_comprovada" in report["projects_by_reason"]
    assert not report["total_sla_approved"]


def test_empty():
    assert audit([])["projects"] == 0


@pytest.mark.parametrize("field,value", [
    ("quantidade_passagens_projeto", 99),
    ("qualidade_trajetoria", "aprovado"),
    ("limitacoes_trajetoria_json", "[]"),
    ("eh_ultima_etapa_observada", True),
    ("versao_regra_trajetoria", "outra"),
])
def test_project_projection_cannot_be_forged(field, value):
    from monday_sla_orcamento.consolidation import build, validate
    from test_consolidation import inputs
    data, _ = build(*inputs())
    data[0][field] = value
    with pytest.raises(ValueError, match="trajetoria"):
        validate(data)


def test_last_flag_is_per_project_not_per_native_item():
    from monday_sla_orcamento.consolidation import build
    from test_consolidation import inputs
    data, _ = build(*inputs())
    assert [r["eh_ultima_etapa_observada"] for r in data] == [False, True]
    assert {r["quantidade_passagens_projeto"] for r in data} == {2}
    assert data[0]["limitacoes_trajetoria_json"] == data[1]["limitacoes_trajetoria_json"]
