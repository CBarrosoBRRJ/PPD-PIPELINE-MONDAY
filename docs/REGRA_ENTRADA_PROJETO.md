# Entrada inicial — decisão posterior à v16

Entrada deve ser o primeiro status conhecido. Não exigir o mesmo dia da criação:
registro posterior pode representar correção. Não alterar datas observadas.
Status nulos anteriores podem preceder a Entrada, se a ordem temporal estiver
comprovada; não representam etapas produtivas ou durações a incluir no KPI.
Outro status conhecido anterior reprova o projeto inteiro para o recorte estrito.

Auditoria candidata: scripts/audit_project_start_cloudshell.py, somente leitura,
usando o artefato ativo verificado por SHA256 e controle estável. Não altera GCP.
Também sinaliza lacunas posteriores, status desconhecidos e fronteiras entre
ambientes sem homologação. Correlação de identidade não prova continuidade.
Datas de criação não são usadas para fabricar a Entrada.

Projetos abertos com início/trecho observado coerentes são candidatos nesta
auditoria; não são entregas nem garantia de histórico vitalício completo.
Contagens de motivos podem se sobrepor. A auditoria mede somente a população
atualmente publicada, não resolve projetos já excluídos pelas regras anteriores.

Estado: seis testes focados e Ruff aprovados. Filtro de produção NÃO aplicado;
v16 permanece ativa. Próximo passo: medir impacto no Cloud Shell, depois integrar
a regra versionada na construção/revalidação e implantar com reconciliação.
Manter fontes e histórico preservados; não executar DELETE manual na tabela.
