# monday_log_viu2

Código da carga única do log viu2 já publicado. Uma linha por evento disponível,
com identificadores nativos e payload original. Não é tabela de SLA tratado.
A orientação atual é BQ para consumo tratado: manter este código não autoriza
novas cargas brutas nem resolve a decisão sobre a tabela já existente.

- `src/monday_log_viu2/archive.py`: coleta/arquivo histórico verificável.
- `src/monday_log_viu2/structured.py`: projeção do evento e schema de exportação.
- `src/monday_log_viu2/publication.py`: publicador legado e helpers Cloud Shell.
- `scripts/`: ferramentas manuais; não fazem parte da agenda diária.
- `tests/`: validação de integridade, paginação e projeção.

Publicador legado contém referências históricas: não executá-lo para recriar
tabelas removidas ou carregar dados novos sem uma migração explícita.
Nenhum dado privado fica nesta pasta. Nenhuma exclusão GCP nesta reorganização.
