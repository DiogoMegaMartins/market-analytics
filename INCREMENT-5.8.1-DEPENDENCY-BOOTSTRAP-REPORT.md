# Market Analytics 5.8.1 — Dependency Bootstrap

## Objetivo
Preparar a instalação offline de `asyncpg` e `ruff` no ambiente de execução do ChatGPT.

## Resultado
- Confirmado que `asyncpg>=0.29` já está declarado nas dependências principais de `backend/pyproject.toml`.
- Confirmado que `ruff>=0.6,<1.0` já está declarado nas dependências `dev`.
- Confirmado que `.github/workflows/ci.yml` instala `.[dev]`, verifica a versão do Ruff, executa `ruff check` e testa a importação de `asyncpg` no job PostgreSQL.
- Adicionado `OFFLINE-DEPENDENCY-INSTALL.md` com instruções para gerar wheels Linux x86_64/Python 3.13, anexar o ZIP e instalar sem índice de pacotes.

## Limitações / validação pendente
- Não foram incluídos wheels no ZIP porque este ambiente não tem acesso de rede ao PyPI.
- `asyncpg` e `ruff` ainda não foram instalados neste ambiente.
- Ruff e a suite completa de testes ainda não foram executados nesta versão.
- Não foram realizadas ligações à Neon, migrações ou alterações à base de dados.

## Próximo passo
O utilizador deve gerar e anexar o ZIP `market-analytics-wheelhouse` seguindo `OFFLINE-DEPENDENCY-INSTALL.md`. Depois será possível instalar os wheels localmente neste ambiente e executar a validação completa.
