"""Read-only coverage audit against pinned published identity map; no credentials/files written."""

import gzip
import hashlib
import json
import subprocess
from collections import Counter

PROJECT = 'gglobo-viu-dados-hdg-prd'
BASE = 'gs://' + PROJECT + '-ppd-pipeline-monday/'
MAP = 'consolidado/primeira_carga/980f2b9c034226347699edb9b8bbc76e652e98dcc1be3abada7a4f13ed315b44/selected_identity.json.gz'
SHA = '486845629229aaa881c38ab87d58cec49811f539642d413d9aa29f07569399eb'


def command(*args):
    return subprocess.check_output(args)


def summarize(mapping, rows):
    linked = {str(r['globocorp_item_id']) for r in mapping['rows']}
    if len(linked) != len(mapping['rows']):
        raise ValueError('Mapa duplicado')
    if len(rows) >= 10000:
        raise ValueError('Limite de resultados exige paginacao')
    totals, with_entry, entries, unlinked = Counter(), Counter(), Counter(), []
    for row in rows:
        item = str(row['item_id'])
        present = str(row['na_consolidada']).lower() == 'true'
        group = 'na_consolidada' if present else 'mapeado_fora_consolidada' if item in linked else 'sem_mapa'
        if present and item not in linked:
            raise ValueError('Consolidada e mapa divergentes')
        totals[group] += 1
        count = int(row['entradas_datadas'])
        entries[group] += count
        if count:
            with_entry[group] += 1
            if group == 'sem_mapa':
                unlinked.append(item)
    return {'itens_por_grupo': dict(totals), 'itens_com_entrada_datada': dict(with_entry),
            'passagens_entrada_datada': dict(entries),
            'ids_sem_mapa_com_entrada_datada': sorted(unlinked)}


def main():
    control_before = command('gcloud', 'storage', 'cat', BASE + 'consolidado/diario/control.json')
    control = json.loads(control_before)
    if control.get('pending') is not None or control['identity']['map_sha'] != SHA:
        raise ValueError('Publicacao pendente ou mapa diferente')
    raw = command('gcloud', 'storage', 'cat', BASE + MAP)
    if hashlib.sha256(raw).hexdigest() != SHA:
        raise ValueError('Checksum divergente')
    mapping = json.loads(gzip.decompress(raw))
    if mapping['version'] != 'selected-identity-v1':
        raise ValueError('Contrato do mapa divergente')
    sql = '''WITH selecionados AS (
      SELECT DISTINCT item_id_globocorp
      FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento`
    ) SELECT g.item_id,
      COUNTIF(g.status_nome = "Entrada" AND g.entrada_status_utc IS NOT NULL) AS entradas_datadas,
      LOGICAL_OR(s.item_id_globocorp IS NOT NULL) AS na_consolidada
    FROM `gglobo-viu-dados-hdg-prd.viu_agenciamento.monday_sla_orcamento_globocorp` g
    LEFT JOIN selecionados s ON g.item_id = s.item_id_globocorp
    GROUP BY g.item_id ORDER BY g.item_id'''
    rows = json.loads(command('bq', '--project_id=' + PROJECT, '--format=json', 'query',
        '--location=US', '--use_legacy_sql=false', '--use_cache=false',
        '--maximum_bytes_billed=1073741824', '--max_rows=10000', sql))
    if command('gcloud', 'storage', 'cat', BASE + 'consolidado/diario/control.json') != control_before:
        raise ValueError('Controle mudou durante auditoria')
    print(json.dumps({'status': 'read_only_coverage', 'cloud_data_modified': False,
                      'map_sha': SHA, **summarize(mapping, rows)}, indent=2))


if __name__ == '__main__':
    main()
