"""Contrato candidato da tabela aprovada; nao habilita publicacao por si so."""
import json
import math

from monday_sla_orcamento.live_cycles import RULE
from monday_sla_orcamento.trajectory import instant

TABLE = 'monday_ciclos_orcamento'
FIELDS = {
    'projeto_id': ('STRING', True), 'ciclo_id': ('STRING', True),
    'numero_ciclo': ('INTEGER', True), 'tipo_ciclo': ('STRING', True),
    'interval_id_inicio': ('STRING', True), 'interval_id_fim': ('STRING', False),
    'item_id_viu2': ('INTEGER', False), 'item_id_globocorp': ('INTEGER', False),
    'inicio_utc': ('TIMESTAMP', True), 'fim_utc': ('TIMESTAMP', False),
    'corte_utc': ('TIMESTAMP', True), 'situacao': ('STRING', True),
    'operacao_horas_corridas': ('FLOAT', False), 'operacao_horas_uteis': ('FLOAT', False),
    'terceiros_horas_corridas': ('FLOAT', False), 'terceiros_horas_uteis': ('FLOAT', False),
    'standby_horas_corridas': ('FLOAT', False), 'standby_horas_uteis': ('FLOAT', False),
    'duracao_completa': ('BOOLEAN', True), 'kpi_entrega_observada': ('BOOLEAN', True),
    'contem_estimativa': ('BOOLEAN', True), 'contem_idade_aberta': ('BOOLEAN', True),
    'quantidade_passagens_operacionais': ('INTEGER', True),
    'motivos_json': ('STRING', True), 'versao_regra': ('STRING', True),
    'versao_calendario': ('STRING', True),
}


def project(result):
    """Verifica chaves entre ciclos e passagens, numeros e datas antes do consumo."""
    passages = {p['interval_id']: p for p in result['passagens']}
    if len(passages) != len(result['passagens']):
        raise ValueError('Ciclos: passagens duplicadas')
    seen, output = set(), []
    for source in result['ciclos']:
        row = {k: v for k, v in source.items() if k != 'motivos'}
        row['motivos_json'] = json.dumps(source['motivos'], ensure_ascii=False)
        if set(row) != set(FIELDS) or row['ciclo_id'] in seen:
            raise ValueError('Ciclos: schema ou chave divergente')
        for key, (kind, required) in FIELDS.items():
            value = row[key]
            if value is None:
                if required:
                    raise ValueError('Ciclos: obrigatorio nulo')
                continue
            if kind == 'STRING' and not isinstance(value, str):
                raise ValueError('Ciclos: texto invalido')
            if kind == 'INTEGER' and (type(value) is not int or value < 1):
                raise ValueError('Ciclos: inteiro invalido')
            if kind == 'BOOLEAN' and type(value) is not bool:
                raise ValueError('Ciclos: booleano invalido')
            if kind == 'FLOAT' and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError('Ciclos: duracao invalida')
            if kind == 'TIMESTAMP':
                instant(value)
        for key in ('interval_id_inicio', 'interval_id_fim'):
            if row[key] is not None:
                passage = passages.get(row[key])
                if not passage or passage['projeto_id'] != row['projeto_id'] or passage['ciclo_id'] != row['ciclo_id']:
                    raise ValueError('Ciclos: relacionamento invalido')
        if row['versao_regra'] != RULE or row['situacao'] not in {'em_andamento', 'entregue', 'interrompido'}:
            raise ValueError('Ciclos: regra/situacao invalida')
        if (row['fim_utc'] is None) != (row['situacao'] == 'em_andamento'):
            raise ValueError('Ciclos: fechamento divergente')
        start, end, cut = instant(row['inicio_utc']), instant(row['fim_utc']), instant(row['corte_utc'])
        if start > cut or (end is not None and not start <= end <= cut):
            raise ValueError('Ciclos: janela invalida')
        if row['kpi_entrega_observada'] and (row['situacao'] != 'entregue'
                or not row['duracao_completa'] or row['contem_estimativa'] or row['contem_idade_aberta']):
            raise ValueError('Ciclos: KPI invalido')
        for cat in ('operacao', 'terceiros', 'standby'):
            gross, useful = row[cat + '_horas_corridas'], row[cat + '_horas_uteis']
            if (gross is None) != (useful is None) or (gross is not None and useful > gross + .001):
                raise ValueError('Ciclos: relogios divergentes')
        seen.add(row['ciclo_id'])
        output.append(row)
    if any(p['ciclo_id'] is not None and p['ciclo_id'] not in seen for p in passages.values()):
        raise ValueError('Ciclos: passagem orfa')
    return output
