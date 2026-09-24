import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[3] / 'scripts/audit_project_start_cloudshell.py'
spec = importlib.util.spec_from_file_location('project_start_audit', path)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def row(order, status, start, end=None, origin='viu2'):
    return dict(projeto_id='p', ordem_etapa=order, status_nome=status,
                entrada_status_utc=f'2026-09-02T{start}:00+00:00',
                saida_status_utc=f'2026-09-02T{end}:00+00:00' if end else None,
                status_terminal=False if status else None, ambiente_origem=origin)


def test_next_day_creation_not_a_rejection():
    r = row(1, 'Entrada', '10:00')
    r['criado_em_origem'] = '2026-09-01T10:00:00Z'
    assert audit.assess([r]) == ([], 0)


def test_null_prefix_allowed_but_not_counted():
    rows = [row(1, None, '09:00', '10:00'), row(2, 'Entrada', '10:00')]
    assert audit.assess(rows) == ([], 1)
    assert audit.summarize(rows)['passagens_candidatas'] == 1


def test_known_status_before_entry_excludes_whole_project():
    rows = [row(1, 'Em revisão', '09:00', '10:00'), row(2, 'Entrada', '10:00')]
    assert audit.summarize(rows)['projetos_candidatos'] == 0


def test_internal_gap_or_null_rejected():
    assert audit.assess([row(1, 'Entrada', '09:00'), row(2, 'Em revisão', '10:00')])[0]
    assert audit.assess([row(1, 'Entrada', '09:00', '10:00'), row(2, None, '10:00')])[0]


def test_migration_not_proven_by_adjacent_times():
    rows = [row(1, 'Entrada', '09:00', '10:00'),
            row(2, 'Em revisão', '10:00', origin='globocorp')]
    assert 'continuidade_entre_ambientes_nao_homologada' in audit.assess(rows)[0]


def test_unfinished_project_not_misclassified_as_missing_start():
    assert audit.assess([row(1, 'Entrada', '09:00', '10:00'),
                         row(2, 'Em revisão', '10:00')]) == ([], 0)
