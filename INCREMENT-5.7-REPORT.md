# Incremento 5.7 — Compatibilidade dos testes de autorização com FastAPI recente

## Objetivo

Corrigir os seis testes unitários reportados pelo utilizador sem alterar a autenticação, a autorização, as rotas de negócio ou a base de dados.

## Alterações

- `backend/tests/unit/test_auth_security.py`: o teste das rotas de gestão de sessões passou a verificar o contrato público OpenAPI (caminhos, métodos e `HTTPBearer`) em vez de filtrar `app.routes` por `APIRoute`.
- `backend/tests/unit/test_authorization_route_coverage.py`: a cobertura de autenticação é verificada pelo OpenAPI; a presença da autorização de empresa é verificada diretamente nas dependências declaradas nos routers de business quality, financial data e metrics; a proteção do router de identidade também é verificada ao nível do router.
- `backend/tests/unit/test_business_quality_workspace_routes.py`: o registo das rotas do workspace de evidências passou a ser verificado pelo OpenAPI, incluindo a segurança Bearer.
- `backend/tests/unit/test_config.py`: o teste de exigência explícita de `DATABASE_URL` ignora o `.env` local e remove variáveis de ambiente de base de dados, tornando o teste independente da máquina do programador.

## Validação executada neste ambiente

- Testes diretamente relacionados com as correções: **9 passaram**.
- Suite `tests/unit`: **180 passaram, 1 falhou**.
- A única falha restante foi `tests/unit/test_dependencies.py::test_database_dependencies_are_importable`, porque `asyncpg` não está instalado neste ambiente de execução. `asyncpg>=0.29` já está declarado nas dependências do projeto (`pyproject.toml`).
- `python -m compileall -q app tests`: passou.
- Ruff não foi executado: o módulo `ruff` não está instalado neste ambiente.

## Segurança e dados

- Não foram alteradas rotas de aplicação, dependências de autenticação/autorização, políticas de funções, migrações ou dados.
- Nenhuma ligação ou escrita no Neon foi efetuada.
- As verificações de autenticação continuam a exigir `HTTPBearer`; os routers company-scoped continuam a declarar `require_company_access`.

## Próxima validação no ambiente do utilizador

Na pasta `backend`, executar:

```cmd
python -m pytest tests/unit -q
python -m ruff check app tests
```

Se `asyncpg` não estiver instalado, executar `python -m pip install -e ".[dev]"` (a dependência `asyncpg` é obrigatória no projeto) e repetir a suite.
