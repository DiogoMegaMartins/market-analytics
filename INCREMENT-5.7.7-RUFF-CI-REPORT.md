# Incremento 5.7.7 — integração Ruff no desenvolvimento e CI

## Objetivo
Tornar a verificação Ruff reproduzível no ambiente local e automática no GitHub Actions, incluindo explicitamente a regra `I` para ordenação/formatação de imports (`I001`).

## Alterações
- Dependência de desenvolvimento alterada para `ruff>=0.6,<1.0`.
- `backend/pyproject.toml`: `extend-select = ["I"]` em `[tool.ruff.lint]`; mantém `line-length = 100`, Python 3.12 e exceções FastAPI `B008`.
- GitHub Actions: criado job independente `backend-quality`, sem dependência de PostgreSQL, que instala `.[dev]`, confirma `python -m ruff --version`, executa `python -m ruff check --output-format=github app tests` e `compileall`.
- README atualizado com instalação, comandos locais e distinção entre correção automática local e validação não-mutável no CI.
- O job PostgreSQL mantém as migrações, testes e smoke tests; não passa a depender da etapa de lint para instalar ferramentas em produção.

## Validação nesta entrega
- `pyproject.toml` lido com `tomllib`: passou.
- Estrutura YAML do workflow validada quando o parser YAML está disponível.
- Ruff não está instalado no ambiente de criação e não há acesso de rede para o instalar; portanto, não foi executado localmente e não se afirma que o código atual esteja Ruff-clean.
- A primeira execução do novo job `backend-quality` no GitHub Actions será a validação efetiva de `I001` e dos restantes avisos. Se falhar, o log do job identificará os ficheiros/linhas a corrigir.

## Segurança e âmbito
- Nenhuma ligação ou escrita na Neon.
- Nenhuma alteração à base de dados, migrações, dados SEC ou lógica financeira.
- CI executa verificações; não aplica `--fix` automaticamente nem altera o repositório.
