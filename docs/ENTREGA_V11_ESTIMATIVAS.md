# V11 — hipótese de saída entre ambientes

Status atualizado: v11 implantada, execução pipeline-monday-f9gbw, publicação
confirmada em 23/09/2026 22:09:47 UTC, consulta BQ e exemplo DBeaver conferidos.
Agenda reativada; próxima execução automática ainda pendente. Não repetir migração.
O procedimento abaixo registra a implantação já realizada.

Base anterior confirmada: v10/v5, execução
pipeline-monday-rbldd em 23/09/2026 21:47:17 UTC, publication_verified=true,
9.648 passagens, 2.209 projetos, 6.227 KPIs e verificações SQL sem divergências.
Operador confirmou retomada da agenda ENABLED 0 6 * * *, America/Sao_Paulo.

Pacote runtime/pipeline-monday-release-20260923-v11-estimativas.zip, 82 arquivos
de código; manifesto SHA256 e compilação Python conferidos. SHA256 do ZIP:
b3d76cf4c003bb6dd6e561e053aa6cab6a563638b088b7cda80e708229cc0a28.
Validação final local: 454 testes aprovados, 3 ignorados; Ruff aprovado.
Build Docker, teste de campos e push confirmados pelo operador, digest
94debc58d1f5eb702abef7489a4f9b6a57500623abe6ce30fe0059474c7f7d3b.

Usuário autorizou estimativa separada usando a próxima entrada, sem reescrever
o observado ou incluir automaticamente no KPI oficial. Contrato candidato
sla-consolidado-estimativas-v6 acrescenta oito campos descritos no PRD.
Política: estimativa-proxima-etapa-v1. Grão permanece passagem; nenhuma tabela extra.
Vínculo é selecionado pela política de identidade, não migração comprovada.

## Ensaio local

Base v5: b676c79b17237437c193bb28fde297ad9452b6ab34250a5bf9670c30ee53a895.
Candidata v6: daba7914c4ccbcf8f6d7d60c1b97e2bce742a62a86b379690a89b48cca069bef.
191 passagens com estimativa; 9.648 linhas e 6.227 valores de KPI preservados.
Nenhum campo anterior alterado, exceto versao_contrato. Datas observadas, lacunas
e continuidade_validada permanecem iguais. Reprodução: validate_estimates_upgrade.py.
No exemplo ABRALE, hipótese de saída 20/09/2026 00:00:39.895647 São Paulo;
701,357 horas corridas / 152,345 úteis. Não representa permanência comprovada.

## Implantação controlada

1. Conferir SHA do ZIP v11, extrair em diretório novo e executar
   migrate_estimates_contract.py plan (somente leitura). Deve conferir fingerprint
   v5 acima e retornar geração. Se a agenda avançou a base, NÃO forçar o hash.
2. Build Docker, teste offline dos campos/versão, push e obter digest.
3. Pausar apenas pipeline-monday-diario; pipeline-monday na imagem nova por digest
   em modo plan,--manifest,/app/pipelines.json, comando pipeline-monday.
4. migrate_estimates_contract.py apply --expected-generation <plano>
   --expected-image <digest>. Guardas compartilhadas: agenda pausada, job parado,
   imagem correta, fingerprint esperado e escrita condicional por geração.
5. Executar daily na nova imagem. Publicação reconcilia schema v5 anterior,
   substitui atomicamente por v6 e verifica conteúdo antes de promover controle.
6. Conferir estimativas (191 nesta base), KPI (6227), 9648 linhas e 2209 projetos,
   e ausência de estimativa em terminais/saída observada. Retomar agenda após recibo.

Não executar scripts de migrações anteriores incluídos como biblioteca. Não
alterar tabela manualmente, apagar locks, tocar IAM/LIA/Terraform ou enviar ao GitHub.
Caso haja falha, conservar agenda pausada e investigar; não voltar à imagem antiga
com identidade do controle nova. Build/push/publicação exigem recibos do operador.

## Consumo

Usar sql/trajetoria_com_estimativas.sql. Manter colunas de saída observada e
estimada visíveis lado a lado. Campo de KPI oficial continua sla_etapa_horas_uteis.
Estimativas devem ser rotuladas no relatório; não usar COALESCE de duração estimada
e oficial para produzir um KPI único. A hipótese usa evento posterior, portanto
não é feature disponível antes dele em previsão ML; evitar vazamento temporal.
