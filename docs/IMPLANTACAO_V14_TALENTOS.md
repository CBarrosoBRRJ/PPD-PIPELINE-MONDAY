# Release v14 / contrato v9 — candidato, nao implantado

## Recibo local

- Suite: 531 testes aprovados, 3 ignorados; Ruff e diff-check aprovados.
- ZIP: `runtime/pipeline-monday-release-20260924-v14-talentos.zip`.
- SHA256: `ce7aaf15905e6a4a39a7e721d0a429d3f22c2c03d93c10486d82c708cc5628d8`.
- Pacote: 100 arquivos de codigo/configuracao mais inventario, sem .env/dados.
- Migracao testada com bloqueio de fingerprint desatualizado e pending,
  CAS preservando active; reconciliacao de schema v8 antes da publicacao v9.
- Build real, migracao e consultas no GCP ainda nao executados nesta revisao.

Objetivo: nome de talento atual e flag de interveniencia na tabela final, sem
perder atributos/equipes nem misturar cadastro atual com historico. Ver PRD do
consolidado e LEGENDA_CADASTRO_SLA.md. Nao altera calendarios, duracoes, corte,
IDs, filtros de escopo nem o grao de passagem. Novos campos sao derivados na
construcao e novamente conferidos antes da publicacao.

## Implantacao controlada

1. Conferir SHA do ZIP source-only; extrair em pasta nova. Plano com
   `python3 migrate_talent_contract.py plan` deve mostrar origem v8 e destino v9.
2. Build por tag nova (v14), registrar digest imutavel. Build nao publica dados.
3. Conferir agenda pausada e nenhuma execucao ativa. Guardar configuracao atual.
   Trocar imagem por digest e manter comando pipeline-monday / args plan.
4. Repetir plano. Apply exige expected-generation, expected-fingerprint e
   expected-image da leitura atual. O script reutiliza motor CAS isolado, nao
   muda a migracao v7→v8, nao altera tabelas e exige os mesmos bloqueios.
5. Mudar para daily e executar. Conferir orchestration_end da execucao exata.
   Nao voltar somente a imagem v13 depois de migrar controle para v9.
6. Validar BQ com auditoria_cadastro_atual.sql e auditoria_talentos.sql; conferir
   chaves, cobertura, origem e NULL nos ambiguos. Amostrar projetos nas tres
   condicoes (exclusivo/interveniencia/ambiguo, se existirem na populacao).
7. Conferir precificacao e campos antigos; nenhum ganho de cobertura inventado.
   Comparar duracoes por interval_id em captura com mesmo corte antes/depois,
   nao apenas contagens totais. Cadastro pode mudar entre capturas.
8. Conferir controles GCS sem pending e os recibos; depois retomar a agenda e
   confirmar proxima execucao automatica. Alerta SMTP ainda exige configuracao
   com segredos rotacionados e teste de recebimento autorizado.

## Limites

Sem acesso local autorizado ao GCP: comandos em producao dependem do Cloud Shell
do operador. Nao declarar homologacao so pelos testes locais ou pelo build.
As colunas antigas sao preservadas para nao quebrar consumidores. Nomes amigaveis
para todos os responsaveis e tipos estao em cadastro_analitico.sql, nao ha DDL de
renomeacao destrutiva. Lista de pessoas/talentos requer ponte no Power BI; nunca
multiplicar passagens e depois somar duracoes. Dashboard e treinamento ML nao
estao automaticamente homologados pela migracao de schema.
