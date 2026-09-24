# Upgrade de precificação — candidato local, 24/09/2026

Não é entrega completa nem recibo de implantação. Produção confirmada segue v12,
contrato de análise v7. Não executar migrações antigas para instalar este candidato.

## Implementado nesta etapa

- Módulo `pricing.py` integrado à construção e validação da consolidada.
- Schema aditivo v8: ciclos de precificação por projeto/origem, dois relógios,
  pausas, contribuições por etapa e motivos de inelegibilidade.
- Totais somente na entrega; leitura v7 preservada para reconciliação.
- Migração `migrate_pricing_contract.py`: plano sem escrita; apply exige geração
  e fingerprint atuais, imagem por digest, agenda pausada, modo plan e nenhuma
  execução ativa. CAS preserva o descritor ativo; não altera tabelas diretamente.
- SQL de consumo candidato e contrato/DDL gerados.

## Bloqueios observados

- Leitura local do job `pipeline-monday` recusada com PERMISSION_DENIED em
  `run.jobs.get`. Não foi iniciada outra autenticação nem alterado IAM.
- Leitura local dos boards 18429499488 e 18429499631 falhou por conexão.
  Não é prova de credencial inválida; não inspecionamos os schemas reais nesta etapa.
- Nenhum recurso GCP foi alterado. Nenhuma senha exposta foi gravada no código.

## Atualização posterior desta implementação

IDs/tipos dos boards confirmados pelo operador via metadata_read_only. Candidatos
de snapshot, publicação recuperável, workers, manifesto com quatro produtos e
enriquecimento cadastro_atual_ implementados. Adaptador opcional SMTP e testes
acrescentados; canal externo não configurado/homologado. Nenhuma implantação GCP
confirmada. Ver [explicação atual](PROJETO_EXPLICADO.md).

## Checklist original (consultar atualização acima)

1. Inspecionar schemas reais dos boards por acesso autorizado; mapear IDs/tipos
   de Marca, Talentos, Interveniência, equipes e tipos Projeto/Input/Output.
2. Implementar os produtos backlog/talentos e enriquecimento com contratos,
   publicação recuperável e testes. Não anunciar essas tabelas como criadas.
3. Implementar alertas e validar canal autorizado com credenciais rotacionadas.
4. Reconciliar o cálculo novo com amostra real e contabilizar cobertura. Testes
   sintéticos não provam a quantidade de ciclos aprovados na produção.
5. Revisar pacote/imagem e plano de migração sobre a geração corrente. Não
   reutilizar fingerprints de 23/09 após a publicação diária de 24/09.
6. Implantar pelo acesso autorizado, executar daily, reconciliar BQ/GCS e retomar
   agenda apenas após sucesso. Confirmar próxima execução agendada.
7. Atualizar relatório/ML com métricas disponíveis e sincronizar revisão aprovada
   no GitHub. Não declarar máquina/GCP/GitHub iguais durante esse desenvolvimento.

Para obter plano de migração no ambiente autorizado, com os dois scripts
`migrate_pricing_contract.py` e `migrate_kpi_contract.py` na mesma pasta:

```bash
python3 migrate_pricing_contract.py plan
```

Esse comando é somente leitura. Não aplicar o candidato parcial antes de fechar
a revisão de escopo e a validação real. Não preencher durações indisponíveis
com estimativas para elevar artificialmente a cobertura.
