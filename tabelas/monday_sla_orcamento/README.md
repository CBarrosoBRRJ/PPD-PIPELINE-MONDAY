# monday_sla_orcamento

Trajetória por projeto selecionado entre viu2 e globocorp. Uma linha por passagem
com entrada conhecida e ordem comprovável; identidade selecionada não significa
continuidade temporal comprovada entre contas. Sem correspondência: fora da seleção.

- `src/monday_sla_orcamento/consolidation.py`: construção, regras e validação.
- `src/monday_sla_orcamento/publication.py`: publicação diária com controle próprio.
- `scripts/`: correspondência, primeira carga, empacotamento e gerador do contrato.
- `docs/CONTRATO_CONSOLIDADO.md`: campos, tipos, nulos e semântica de fechamento.
- `sql/`: schema de referência, não transformação SQL.
- `tests/`: regras, carga inicial e recuperação da publicação diária.

Terminal encerra SLA na entrada, sem acumular duração depois. Saída desconhecida
de não terminal não comprova abandono. Não inventar datas, vínculos ou duração.
Negócio Fechado não foi ativado como terminal nesta reorganização.

Publicação v8/v3 conferida: 9.648 linhas / 2.209 projetos; integração diária implantada.
Contrato v4 de consumo direto implementado localmente, ainda não implantado.
Filtrar contrato v3 + elegivel_comparacao=true + aprovado_etapa_origem_v1 somente
após recibo de publicação; não consumir total entre contas como homologado.
Após v4 publicada, usar sla_etapa_horas_uteis para média, sem converter NULL em zero.
Ver [contrato de consumo](PRD.md) e [homologação](../../docs/HOMOLOGACAO_KPI_ETAPA.md). Exclusões implementadas e testadas
conforme [política compartilhada](../../docs/REGRAS_ESCOPO_SLA.md).
Ver [operação](../../docs/ATUALIZACAO_DIARIA_CONSOLIDADO.md).
