# Sprint 4.2.4 — Security Integration & Deployment Verification

## Objetivo

Criar um caminho repetível para validar o conjunto backend + PostgreSQL + frontend, em vez de inferir prontidão de produção a partir de testes unitários isolados.

## Alterações

- Pipeline GitHub Actions com PostgreSQL 16 como serviço.
- Instalação das dependências backend e execução das migrações até `0011_auth_security`.
- Testes automatizados contra PostgreSQL real para verificar a revisão aplicada e o trigger append-only de `auth_audit_events`.
- Smoke tests HTTP de `/health/live` e `/health/ready`.
- Verificação estática de cobertura das dependências de autenticação e autorização nas rotas de identidade, métricas, dados financeiros e Business Quality.
- Política de roles extraída para função testável (`allowed_roles_for_company_write`).
- Script local `scripts/verify-deployment.sh` para repetir migrações, testes, typecheck e build.
- Corrigido o `.env.example` do backend: os parâmetros SEC estavam numa única linha com sequências `\n` literais, em vez de linhas de ambiente separadas.
- Adicionadas dependências de tipos TypeScript e comando `npm run typecheck`.

## Como executar localmente

Pré-requisitos: Docker com Compose, Python 3.12+, Node.js 22+, npm.

```bash
docker compose up -d db
export DATABASE_URL='postgresql+asyncpg://market:market_dev_password@localhost:5432/market_analytics'
export SECRET_KEY='local-verification-secret-key-change-this-please-123456'
./scripts/verify-deployment.sh
```

O script aplica migrações à base de dados indicada em `DATABASE_URL`. Não o executar contra produção sem backup, janela de manutenção e aprovação explícita.

## Resultado de validação nesta execução

- `pytest -q` antes das novas verificações: 121 testes passaram.
- `alembic upgrade head --sql`: gerou SQL para todas as migrações até `0011_auth_security`.
- Importação FastAPI e registo de rotas: verificados no ambiente local.
- PostgreSQL real: **não executado** — Docker/servidor PostgreSQL não estão disponíveis neste ambiente.
- Frontend: **não validado** — `npm install` excedeu o limite de execução; `next build` e `tsc --noEmit` não foram executados.

Os novos testes de integração PostgreSQL são ativados pela variável `TEST_DATABASE_URL` e executados no CI após `alembic upgrade head`.

## Limitações e riscos remanescentes

1. A pipeline foi criada, mas a execução no GitHub Actions ainda depende de um push/PR; não há resultado remoto nesta entrega.
2. A integração real do refresh token sob concorrência ainda deve ser testada end-to-end. Duas renovações simultâneas com o mesmo refresh token podem ser interpretadas como reutilização e revogar a sessão; o frontend deve evitar renovações paralelas e o backend deverá considerar uma política de concorrência explícita.
3. Não há teste completo de isolamento multi-tenant com dois utilizadores e duas empresas reais em PostgreSQL.
4. MFA, recuperação de conta, política de password, gestão de chaves/rotação de `SECRET_KEY`, proteção de proxy confiável e monitorização de abuso continuam pendentes.
5. A configuração de cookies/CORS em staging/produção precisa de ser validada com os domínios reais e HTTPS.
6. O rate limit de login está persistido em PostgreSQL, mas carece de testes de carga e de política operacional de retenção/limpeza.

## Critério de aceitação

O sprint fornece testes e automação reproduzíveis. Não certifica a aplicação como pronta para produção. A aceitação operacional requer que a pipeline execute com sucesso num ambiente CI e que os testes PostgreSQL e frontend passem.
