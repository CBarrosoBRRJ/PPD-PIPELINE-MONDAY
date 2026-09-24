"""Explicit current Globocorp context; never historical authorship or identity merge."""

import json

ATTRIBUTES = ('marca', 'talentos_exclusivos_json', 'interveniencia', 'orcamento_json',
              'talent_manager_json', 'gp_json', 'conteudo_json', 'producao_json',
              'audiencia_json', 'tipo_projeto', 'tipo_input', 'tipo_output')
FIELDS = {**{'cadastro_atual_' + key: ('STRING', False) for key in ATTRIBUTES},
          'cadastro_atual_capturado_em': ('TIMESTAMP', False),
          'cadastro_atual_origem_json': ('STRING', False)}


def project(row):
    result = dict.fromkeys(FIELDS)
    raw = row.get('cadastro_atual_origem_json')
    if raw is None:
        return result
    source = json.loads(raw)
    if (source.get('board_id') != 18429499488 or source.get('item_id') != row['item_id_globocorp']
            or source.get('versao_contrato') != 'board-snapshot-v1'
            or not source.get('capturado_em')):
        raise ValueError('Consolidacao: cadastro atual com identidade divergente')
    result.update({'cadastro_atual_' + key: source[key] for key in ATTRIBUTES})
    result.update(cadastro_atual_capturado_em=source['capturado_em'], cadastro_atual_origem_json=raw)
    return result
