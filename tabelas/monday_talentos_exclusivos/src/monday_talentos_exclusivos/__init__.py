"""All talent-board groups; table name does not filter non-exclusive/finalized items."""

SPEC = {
    'table': 'monday_talentos_exclusivos', 'board_id': 18429499631,
    'columns': {
        'nome_artistico': ('text_mm6jdh8c', 'text'),
        'status_nome': ('color_mm6j81gv', 'status'),
        'vinculo': ('color_mm6ktp82', 'status'),
        'talent_manager_json': ('multiple_person_mm6j7jwr', 'people'),
        'orcamento_json': ('multiple_person_mm6jmy1j', 'people'),
        'producao_artistica_json': ('dropdown_mm6nvaq0', 'dropdown'),
        'performance_json': ('multiple_person_mm6jxhsa', 'people'),
        'executivo_json': ('multiple_person_mm6jz2mj', 'people'),
        'atendimento_json': ('multiple_person_mm6jn0y', 'people'),
    },
}
