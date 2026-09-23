# V10 — trajetória legível e validação preventiva

Status: candidata local; nenhuma operação GCP executada pelo assistente.
Pacote: runtime/pipeline-monday-release-20260923-v10-trajetoria.zip, 80 arquivos
de código, manifesto SHA256 conferido. SHA256 do ZIP:
c2e4970ae60cd6af0e810ecc7cb256b913a4954b65a75afb7daebf0a78d66cb3.
Suíte completa: 430 aprovados / 3 ignorados; teste adicional do wrapper v5 e teste
do wrapper v4: 2 aprovados. Ruff aprovado. Build Docker/GCP ainda não executado.
Produção confirmada pelo operador: v9, execução pipeline-monday-9qkxr,
publicação em 23/09/2026 21:11:12 UTC e agenda retomada às 06h São Paulo.

Contrato novo sla-consolidado-trajetoria-v5. Mantém 9.648 passagens / 2.209
projetos e os 6.227 valores de KPI da captura validada. Cinco campos adicionais
expõem quantidade de passagens, qualidade/motivos por projeto, última observação
e versão da regra. Não corrige datas por suposição nem aprova tempo total/ML.

Base v4 reconciliada offline:
3c3ee3cb5a92a96052687300f45efd287ff440f0620d169db4fd64aa961e8f78.
Candidata v5:
b676c79b17237437c193bb28fde297ad9452b6ab34250a5bf9670c30ee53a895.
Se a publicação remota avançou, o plano deve bloquear; não alterar o hash para
forçar migração. Auditar a nova publicação antes de preparar outro pacote.

## Implantação pelo operador

1. Upload do ZIP v10 e conferência do SHA256 fornecido na entrega.
2. Extrair em diretório temporário novo; executar migrate_trajectory_contract.py plan.
   Somente leitura: confirma identidade v4, fingerprint esperado e geração atual.
3. Build Docker do código conferido, testar plan, push e registrar digest imutável.
4. Pausar apenas pipeline-monday-diario; configurar somente pipeline-monday na
   imagem nova por digest, command pipeline-monday, args plan,--manifest,/app/pipelines.json.
5. migrate_trajectory_contract.py apply --expected-generation <geração do plano>
   --expected-image <digest>. Verifica agenda pausada, job em plan e ausência
   de execuções em andamento; muda somente identidade do controle com CAS.
6. Atualizar args para daily,--manifest,/app/pipelines.json e executar com --wait.
   O escritor lê a v4 anterior, publica v5 atomicamente e verifica conteúdo integral.
7. Conferir publication_verified, contrato e campos; retomar agenda após sucesso.

Não repetir migrations consumption/kpi incluídas como biblioteca. Não usar ALTER,
UPDATE manual, não apagar locks e não executar imagem antiga após migrar controle.
LIA, Terraform, IAM, outras tabelas e GitHub não são modificados.

## Aceite de consumo

Usar projeto_id, ordem_etapa para trajetória; item_id é da origem. BQ não tem
ordem física garantida: toda consulta de trajetória precisa de ORDER BY.
sql/trajetoria_projeto.sql exige parâmetro projeto_id. sql/qualidade_projetos.sql
conta uma última etapa observada por projeto. sql/kpi_consumo.sql segue válido.
Para médias, usar sla_etapa_horas_uteis, nunca substituir NULL por zero.

Validar: COUNT(*)=9648, COUNT(DISTINCT projeto_id)=2209,
COUNTIF(eh_ultima_etapa_observada)=2209, COUNT(sla_etapa_horas_uteis)=6227;
quantidade_passagens_projeto deve coincidir com COUNT(*) OVER(PARTITION BY projeto_id).
Qualidade do projeto não substitui validação individual da etapa.
