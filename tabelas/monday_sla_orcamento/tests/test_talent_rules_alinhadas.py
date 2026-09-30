from monday_sla_orcamento.talent_context import exclusion_reasons, is_pool


def ctx(exclusivos, inter=""):
    import json
    return {"talentos_exclusivos_json": json.dumps(exclusivos), "interveniencia": inter}


def test_separadores_e_coletivos_sao_pool_como_no_filtro_globocorp():
    assert is_pool(exclusion_reasons(ctx([], "Fulano, Ciclano")))
    assert is_pool(exclusion_reasons(ctx([], "Ana & Bia")))
    assert is_pool(exclusion_reasons(ctx(["Podpah"])))
    assert exclusion_reasons(ctx(["Maria Silva"], "maria silva")) == []
    assert exclusion_reasons(ctx(["Maria"], "João")) == ["talento_ambas_colunas"]
