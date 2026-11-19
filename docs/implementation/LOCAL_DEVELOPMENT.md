# Desenvolvimento local

## Requisitos
- Python 3.12+
- Node.js 22 LTS
- Docker Engine/Desktop com Compose plugin (para o perfil integrado)
- Git

## Opção A — Stack integrada em contentores (recomendada para validação local)

1. Copiar `.env.compose.example` para `.env` na raiz do repositório.
2. Gerar segredos hexadecimais únicos, por exemplo `openssl rand -hex 32`, e substituir `POSTGRES_PASSWORD` e `SECRET_KEY`.
3. Definir um contacto válido em `SEC_USER_AGENT`.
4. Iniciar a stack:

   ```bash
   docker compose -f docker-compose.app.yml up --build -d
   ```

5. Executar o smoke test:

   ```bash
   ./scripts/smoke-test.sh
   ```

O serviço `migrate` aplica as migrações Alembic uma única vez. A API só inicia depois da conclusão bem-sucedida. A interface fica em `http://localhost:3000` e a API em `http://localhost:8000`. O URL público da API é embutido no build do frontend através de `NEXT_PUBLIC_API_BASE_URL`.

## Opção B — Desenvolvimento com processos locais

### Base de dados
1. Copiar `backend/.env.example` para `backend/.env` e ajustar os valores.
2. Na raiz: `docker compose up -d db`.
3. Confirmar PostgreSQL em `localhost:5432`.

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e '.[dev]'
alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Verificação

A suite backend corre com `cd backend && pytest -q`. Cinco testes de integração requerem PostgreSQL real e são ignorados quando não existe uma base de testes configurada. A CI executa migrações e testes contra PostgreSQL e faz typecheck/build do frontend, além de construir as imagens Docker.

O perfil integrado é destinado a desenvolvimento e pré-produção. Não equivale a certificação de produção; consultar `docs/operations/deployment-packaging.md` e os runbooks operacionais.
