"""Current talent source projection; no identity inference or passage expansion."""

import json
import re
import unicodedata

SCOPE_RULE = 'talento-cadastro-unico-v1'


def exclusion_reasons(source):
    """Whole-project scope based on verified current registration, not historical claims."""
    raw = source.get('talentos_exclusivos_json')
    names = json.loads(raw) if raw is not None else []
    if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
        raise ValueError('Talentos: lista de exclusivos invalida')
    names = [name.strip() for name in names if name.strip()]
    inter = source.get('interveniencia')
    if inter is not None and not isinstance(inter, str):
        raise ValueError('Talentos: interveniencia invalida')
    inter = (inter or '').strip()
    reasons = []
    if names and inter:
        reasons.append('talento_ambas_colunas')
    if not names and not inter:
        reasons.append('talento_nao_informado')
    if len(names) > 1:
        reasons.append('talento_multiplo')
    if any(re.search(r'\bsquad\b', unicodedata.normalize('NFKC', text).casefold())
           for text in [*names, inter]):
        reasons.append('talento_squad')
    return reasons

FIELDS = {
    'talento_nome_atual': ('STRING', False),
    'eh_interveniencia': ('BOOLEAN', False),
    'talentos_atuais_json': ('STRING', False),
    'situacao_talento_atual': ('STRING', True),
}


def project(row):
    result = dict.fromkeys(FIELDS)
    result['situacao_talento_atual'] = 'sem_cadastro'
    if row.get('cadastro_atual_origem_json') is None:
        return result
    raw = row.get('cadastro_atual_talentos_exclusivos_json')
    names = json.loads(raw) if raw is not None else []
    if not isinstance(names, list) or any(not isinstance(name, str) for name in names):
        raise ValueError('Talentos: lista de exclusivos invalida')
    entries = [{'nome': name.strip(), 'eh_interveniencia': False,
                'origem': 'talentos_exclusivos', 'texto_nao_estruturado': False}
               for name in names if name.strip()]
    inter = row.get('cadastro_atual_interveniencia')
    if inter is not None and not isinstance(inter, str):
        raise ValueError('Talentos: interveniencia invalida')
    inter = (inter or '').strip()
    if inter:
        entries.append({'nome': inter, 'eh_interveniencia': True,
                        'origem': 'interveniencia', 'texto_nao_estruturado': True})
    result['talentos_atuais_json'] = json.dumps(entries, ensure_ascii=False)
    if not entries:
        result['situacao_talento_atual'] = 'nao_informado'
    elif inter and len(entries) > 1:
        result['situacao_talento_atual'] = 'ambas_origens'
    elif len(entries) > 1:
        result['situacao_talento_atual'] = 'multiplos_exclusivos'
    elif inter and re.search(r'[,;\n\r+&/]', inter):
        result['situacao_talento_atual'] = 'interveniencia_requer_revisao'
    else:
        # A single source label is not a certified person or contractual relationship.
        result.update(talento_nome_atual=entries[0]['nome'],
                      eh_interveniencia=entries[0]['eh_interveniencia'],
                      situacao_talento_atual='rotulo_unico_na_origem')
    return result
