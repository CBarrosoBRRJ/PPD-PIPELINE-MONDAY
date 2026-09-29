# Escala e custo — como os pipelines Monday crescem sem quebrar

Padrão adotado em 28/09/2026 para este pipeline e para os próximos. Objetivo: rodar
todo dia, sem estourar memória nem prazo, com custo previsível e baixo.

## O problema que motivou o padrão

O estado do SLA Globocorp guardava uma foto completa de cada item **todos os dias**,
e **81%** dessas fotos eram cópias idênticas. Com isso:

- em 11 dias, carregar o estado já exigia 1,2 GB de memória, com pico de 2,9 GB;
- o job tem 8 GB, então estouraria em poucas semanas.

## Os seis princípios

1. **O bruto fica num arquivo barato, nunca na memória.** A resposta completa do Monday
   de cada dia vai para um arquivo compactado e imutável no GCS:
   `…/bronze/<tipo>/dt=AAAA-MM-DD/`. Serve para auditoria e reprocessamento, e custa
   centavos por ano.
2. **O estado guarda mudanças, não cópias.** Uma nova versão do item só é gravada quando
   um campo usado pelas regras muda. O bruto fica apenas na versão mais recente, que é a
   única que as regras leem. O estado cresce com o **trabalho real**, e não com
   "itens × dias".
3. **Derivados são recalculados, não acumulados.** Tabelas que saem do cálculo (pessoas,
   linhas diárias) são refeitas a cada execução. Linha diária só existe para o que está
   aberto; projeto encerrado não gera linha nova por dia.
4. **Publicar é tudo ou nada; verificar é barato.** A carga no BigQuery é uma transação
   única, com um journal gravado antes. As regras validam a **nova** publicação. O que já
   está publicado é conferido só pelo hash do conteúdo, para que uma mudança de regra
   nunca trave a produção.
5. **Avisar antes de quebrar:**
   - evento `state_size` a cada gravação, com aviso acima de 15 MB (hoje ~5 MB);
   - alerta de "25 h sem sucesso";
   - prazo mínimo por produto;
   - encerramento gracioso que libera as travas.
6. **Nada fica ligado sem uso.** Um Cloud Run Job por dia, por alguns minutos, sem
   servidor sempre ativo. O BigQuery recebe cargas pequenas; o GCS guarda poucos MB por dia.

## Números medidos (estado real de 28/09/2026)

| Item | Antes | Depois |
| :--- | :-: | :-: |
| Fotos de itens no estado | 53.005 | 10.566 |
| Estado comprimido | 24,7 MB | 4,8 MB |
| Memória ao carregar (pico) | 1.238 MB (2.906 MB) | 200 MB (515 MB) |
| Linhas diárias internas | 124.232 | 28.531 |
| Crescimento do estado | ~2,8 MB por dia | só as mudanças reais (~60 itens por dia) |

A tabela publicada foi recalculada nas duas formas e ficou idêntica.

## Custo

- **Cloud Run Job:** 2 vCPU e 8 GB, alguns minutos por dia. É o maior item.
- **Redução de memória:** depois de 7 dias com `state_size` estável abaixo de 10 MB, dá para
  baixar para 4 GB (`gcloud run jobs update pipeline-monday --memory=4Gi`). A economia é
  moderada, porque a vCPU pesa mais que a memória.
- **GCS:** o arquivo bruto diário tem cerca de 1 MB comprimido, algo como 0,4 GB por ano,
  o que custa centavos. Gerações antigas do estado (~5 MB cada) podem ganhar uma regra de
  ciclo de vida de 90 dias quando o volume justificar.
- **BigQuery:** as cargas são transações pequenas; a leitura de verificação usa a listagem
  de linhas, que não é cobrada como consulta.

## Checklist para um pipeline novo

- [ ] Prefixo GCS próprio e permissão condicionada a esse prefixo, nunca ao bucket inteiro.
- [ ] Bruto diário em `bronze/…/dt=` (append-only); estado só com versões e agregados.
- [ ] Nenhuma tabela interna que cresça com "entidades × dias" sem limite.
- [ ] Publicação transacional com journal e verificação por hash.
- [ ] Evento de tamanho do estado e entrada no manifesto do coordenador, com dependências.
- [ ] Teste de regressão de tamanho: simular 365 dias e medir a memória.
