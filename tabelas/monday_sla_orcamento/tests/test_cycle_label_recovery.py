"""A recovered label must not bridge gaps or source boundaries."""

import json

import pytest
from monday_sla_orcamento.consolidation import TERMINAL_LABELS, annotate_closures


def chain():
    rows = []
    for start, end, label in [("10", "11", "Entrada"),
                              ("11", "12", "Em Elaboração"),
                              ("12", None, "Encerrado")]:
        rows.append({"ambiente_origem": "viu2", "status_nome": label,
                     "entrada_status_utc": f"2026-06-19T{start}:00:00+00:00",
                     "saida_status_utc": f"2026-06-19T{end}:00:00+00:00" if end else None,
                     "pendencias_json": json.dumps(["validacao_negocio_pendente"]),
                     "duracao_horas": 1.0 if end else None,
                     "duracao_horas_uteis": 1.0 if end else None})
    return rows


def test_recovered_intermediate_label_enables_only_observed_source_cycle():
    unknown = chain()
    unknown[1]["status_nome"] = None
    annotate_closures(unknown, TERMINAL_LABELS)
    assert unknown[-1]["tempo_ciclo_observado_horas"] is None
    recovered = chain()
    annotate_closures(recovered, TERMINAL_LABELS)
    assert recovered[-1]["tempo_ciclo_observado_horas"] == 2.0
    assert recovered[-1]["duracao_horas"] is None
    assert "validacao_negocio_pendente" in recovered[-1]["pendencias_json"]


@pytest.mark.parametrize("barrier", ["gap", "source", "overlap", "unknown"])
def test_recovered_label_does_not_override_cycle_barriers(barrier):
    rows = chain()
    if barrier == "gap":
        rows[0]["saida_status_utc"] = "2026-06-19T10:59:59+00:00"
    elif barrier == "source":
        rows[1]["ambiente_origem"] = "globocorp"
    elif barrier == "overlap":
        rows[1]["pendencias_json"] = json.dumps(["sobreposicao_temporal_duracao_bloqueada"])
    else:
        rows[1]["status_nome"] = None
    annotate_closures(rows, TERMINAL_LABELS)
    assert rows[-1]["tempo_ciclo_observado_horas"] is None
