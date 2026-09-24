# Recibo local — 23/09/2026

- Python: `python -m pytest -q` — 465 passed, 3 skipped.
- Ruff: `python -m ruff check .` — aprovado.
- HTML: inspeção visual em Edge headless, desktop 1440×1100 e celular 390×844.
- Navegação das cinco páginas, ausência de overflow horizontal externo e erros JS: aprovados.
- Cenário em 30%: 1.080 h de exposição / 120 ciclos = 9,0 h/ciclo: aprovado.
- SQL diagnóstico: campos conferidos contra schema local; não executado no BQ.
- DAX/modelo: exemplos e rascunhos, não executados no Desktop nem publicados.

Limite: este recibo não homologa o KPI ponta a ponta, uma conexão Power BI, RLS,
atualização no serviço, modelos ML ou a execução automática do dia seguinte.
Documentação e protótipo não exigem mudança de imagem/contrato no GCP.

## Adição de 24/09 — primeira página

- Referência `fase1.html` renderizada em Edge headless a 1440 px e 390 px:
  título correto, sem transbordamento horizontal nem erros JavaScript;
  inspeção visual desktop e celular concluída.
- Campos declarados da fonte (19) conferidos contra `consolidated_schema.json`:
  nenhum campo ausente. Todas as medidas da primeira página constam nos rascunhos.
- `git diff --check` aprovado para os arquivos alterados.
- DAX e Power BI Desktop não executados: nenhum PBIP ligado ao BigQuery foi criado.
  Autenticação local do GCP ficou fora deste trabalho, conforme orientação do usuário.
