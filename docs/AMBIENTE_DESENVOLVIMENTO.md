# Ambiente de desenvolvimento

Configuração recomendada para trabalhar no `PIPELINE-MONDAY` pelo VS Code no Windows.

## Extensões

As recomendações compartilhadas estão em `.vscode/extensions.json`. O conjunto cobre Python/Ruff/Pylance, Terraform, GitHub Actions, contêineres, Google Cloud, YAML/TOML/Markdown, Codex, Claude Code, Gemini Code Assist e Gemini CLI Companion.

Depois de instalar ou atualizar extensões, execute **Developer: Restart Extension Host** ou reabra o VS Code para carregar as novas versões. O interpretador padrão do workspace é `.venv/Scripts/python.exe`.

## MCPs

O workspace configura os mesmos servidores em dois clientes:

- `.vscode/mcp.json`: suporte MCP nativo do VS Code.
- `.mcp.json`: Claude Code e clientes compatíveis.

Servidores configurados:

- `github`: servidor remoto oficial, com autenticação OAuth do cliente.
- `gcloud`: servidor oficial Google Cloud executado via Node.js; usa a identidade ativa do Google Cloud CLI.
- `terraform`: servidor oficial HashiCorp em contêiner local, usando o registro público sem token privado.

Nenhum segredo fica nesses arquivos. Na primeira utilização, o VS Code/Claude pode solicitar confiança no servidor e autenticação OAuth. Para operações GCP, faça login pelo Google Cloud CLI no seu terminal e confira projeto/conta antes de executar comandos que alterem recursos.

O MCP do Google Cloud depende de Node.js 20+ e do `gcloud`. O MCP Terraform depende do Docker Desktop em execução. A configuração não concede permissões novas: cada servidor usa as permissões da identidade ativa.

## Verificação rápida

```powershell
code --list-extensions --show-versions
claude --version
claude mcp list
gemini --version
gcloud version
terraform version
docker version
python -m pytest -q
```

Ao renomear ou mover a pasta, recrie a `.venv` se algum ativador conservar o caminho absoluto anterior.
