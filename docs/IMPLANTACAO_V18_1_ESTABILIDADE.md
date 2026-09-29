# Implantação v18.1 — estabilidade (28/09/2026)

> **Pacote substituído por [IMPLANTACAO_V19.md](IMPLANTACAO_V19.md)**, que inclui todas estas correções.
> Use este documento para os passos de segurança e alerta, e como referência técnica.

Release só de correções técnicas. **Não muda nenhuma tabela, coluna ou regra de
negócio publicada.** O que muda:

| Correção | Efeito medido com o estado real de produção |
| :--- | :--- |
| Fotos diárias dos itens guardadas só quando o item muda | Estado de 24,7 MB para **4,8 MB**; memória ao carregar de 1,2 GB para **0,2 GB** (pico de 2,9 GB para 0,5 GB) |
| Foto bruta completa do dia arquivada em GCS (`sla_orcamento/bronze/item_snapshots/dt=AAAA-MM-DD/`) | Nada se perde; o arquivo não é carregado na memória |
| Linha diária interna só para status não encerrados | Tabela interna de 124 mil para 28 mil linhas; não cresce mais com projetos fechados |
| Aviso `state_size` a cada gravação do estado | Alerta antecipado se o estado passar de 15 MB |
| Verificação da consolidada por hash do conteúdo | Uma troca de regra ou da biblioteca de feriados não trava mais a execução diária |
| Coordenador com prazo mínimo por produto e encerramento gracioso | Não começa um produto sem tempo; libera travas em vez de deixá-las presas |
| Guarda contra logs do Monday fora de ordem | Evita perda silenciosa de eventos |
| Scripts legados abortam | Impossível recriar `pipeline-orcamento`, a agenda antiga ou `log_monday_viu2` por engano |

Tabela publicada (Gold), quarentena e qualidade recalculadas com o estado real
antes e depois da compactação: **idênticas, linha a linha**. Testes: 628 aprovados.

Pacote: `runtime/pipeline-monday-release-20260928-v18.1-estabilidade.zip`
SHA256 `51b145b05b9b5047211bb7bed395bd884458862988de56b9db78c8ead833f20d` (108 arquivos).

Imagem atual (para voltar atrás):
`us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday@sha256:dd3ab2619c6e489ca084562e81a947f4e8ac8b723f2b30bfd549071435e88a65`

## Passo a passo (Caio executa no Cloud Shell)

Faça fora da janela das 05:30 às 07:00 (a agenda roda às 06:00). Não precisa pausar a agenda.

1. **Enviar o pacote.** No Cloud Shell, clique em ⋮ → *Fazer upload* e escolha o ZIP. Confira o hash:
   ```bash
   sha256sum pipeline-monday-release-20260928-v18.1-estabilidade.zip
   ```
   O resultado tem de começar com `51b145b0`. Se não bater, pare.

2. **Gerar a imagem.**
   ```bash
   rm -rf release-v18-1 && mkdir release-v18-1
   unzip -q pipeline-monday-release-20260928-v18.1-estabilidade.zip -d release-v18-1
   cd release-v18-1
   gcloud builds submit . --project=gglobo-viu-dados-hdg-prd \
     --tag=us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday:v18-1
   ```
   Esperado: `STATUS: SUCCESS`.

3. **Pegar o digest.** A implantação usa sempre o digest, nunca a tag:
   ```bash
   gcloud artifacts docker images describe \
     us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday:v18-1 \
     --format='value(image_summary.digest)'
   ```
   Anote o valor `sha256:...`.

4. **Confirmar que nada está rodando.** Todas as execuções listadas devem estar concluídas:
   ```bash
   gcloud run jobs executions list --job=pipeline-monday --project=gglobo-viu-dados-hdg-prd \
     --region=us-central1 --limit=3
   ```

5. **Trocar a imagem do job.** Troque `DIGEST` pelo valor do passo 3:
   ```bash
   gcloud run jobs update pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 \
     --image=us-central1-docker.pkg.dev/gglobo-viu-dados-hdg-prd/viu-pipelines/pipeline-monday@DIGEST
   gcloud run jobs describe pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 \
     --format='yaml(spec.template.spec.template.spec.containers[0].image,spec.template.spec.template.spec.containers[0].args)'
   ```
   Os argumentos têm de continuar `daily, --manifest, /app/pipelines.json`.

6. **Executar agora para validar.** Hoje o SLA Globocorp aparece como `skipped`, porque já rodou às 06:00. Os demais produtos rodam normalmente.
   ```bash
   gcloud run jobs execute pipeline-monday --project=gglobo-viu-dados-hdg-prd --region=us-central1 --wait
   gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="pipeline-monday" AND jsonPayload.event="orchestration_end"' \
     --project=gglobo-viu-dados-hdg-prd --order=desc --limit=1 --format='json(timestamp,jsonPayload.status,jsonPayload.products)'
   ```
   Esperado: `status: success`, e `publication_verified: true` nos produtos.

7. **Conferir amanhã, depois das 06:00.** A compactação acontece na primeira execução diária do SLA:
   ```bash
   gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="pipeline-monday" AND jsonPayload.event="state_size"' \
     --project=gglobo-viu-dados-hdg-prd --order=desc --limit=2 --format='json(timestamp,jsonPayload)'
   ```
   Esperado: `compressed_bytes` perto de 5.000.000 e `warning: false`.

**Voltar atrás, se algo falhar:** repita o passo 5 com o digest atual (`sha256:dd3ab261…`, acima).
O estado compactado continua legível pela versão anterior. Não apague travas, journals nem tabelas.

## Segurança: remover permissão ampla da conta de deploy

A conta `deploy-sla-orcamento` tem `roles/run.developer` no **projeto inteiro**. Com isso,
ela alcança jobs de outras iniciativas, inclusive a LIA. Ela só servia ao deploy automático
do GitHub, que está desligado.

```bash
gcloud projects remove-iam-policy-binding gglobo-viu-dados-hdg-prd \
  --member="serviceAccount:deploy-sla-orcamento@gglobo-viu-dados-hdg-prd.iam.gserviceaccount.com" \
  --role="roles/run.developer" --condition=None
```

Para conferir, rode o comando abaixo. A conta não deve mais aparecer:

```bash
gcloud projects get-iam-policy gglobo-viu-dados-hdg-prd --flatten=bindings[].members \
  --filter=bindings.role:roles/run. --format='table(bindings.role,bindings.members)'
```

Para desfazer, rode o mesmo comando trocando `remove-iam-policy-binding` por `add-iam-policy-binding`.

## Alerta: "o job não rodou"

Hoje só existe alerta de erro. Se a agenda não disparar, ninguém fica sabendo.
O alerta abaixo avisa quando passarem 25 horas sem nenhuma execução com sucesso (conta os sucessos numa janela de 25 h e dispara também se não houver dado nenhum).

```bash
gcloud logging metrics create pipeline_monday_sucesso --project=gglobo-viu-dados-hdg-prd \
  --description="pipeline-monday concluído com sucesso" \
  --log-filter='resource.type="cloud_run_job" AND resource.labels.job_name="pipeline-monday" AND jsonPayload.event="orchestration_end" AND jsonPayload.status="success"'

gcloud beta monitoring channels list --project=gglobo-viu-dados-hdg-prd --format='table(name,displayName)'

gcloud alpha monitoring policies create --project=gglobo-viu-dados-hdg-prd \
  --policy-from-file=orquestracao/deploy/alerta_sem_execucao.json \
  --notification-channels=CANAL
```

Troque `CANAL` pelo `name` de um dos canais já criados. Custo: zero, porque métricas
de log e alertas desse volume ficam dentro da cota gratuita.
