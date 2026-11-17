# Neon setup — Increment 5

Set `APP_ENV=staging` or `production` only with an explicit `DATABASE_URL`, a
unique `SECRET_KEY`, `APP_DEBUG=false`, and a TLS-enabled remote PostgreSQL URL.
Neon URLs using `postgres://` or `postgresql://` are normalized to asyncpg;
`sslmode=require` is accepted and normalized to `ssl=require`.

Use the pooled URL in `DATABASE_URL` for application traffic. Set the direct
non-pooled URL in `DATABASE_URL_UNPOOLED` for Alembic migrations. Do not put
either real URL in a committed file.

```powershell
Copy-Item .env.example backend/.env
$env:DATABASE_URL = 'postgresql+asyncpg://USER:PASSWORD@HOST/DB?ssl=require&channel_binding=require'
$env:DATABASE_URL_UNPOOLED = 'postgresql+asyncpg://USER:PASSWORD@HOST/DB?ssl=require&channel_binding=require'
cd backend
pip install -e '.[dev]'
alembic upgrade head       # uses DATABASE_URL_UNPOOLED when provided
pytest -q tests/unit
pytest -q tests/integration  # uses TEST_DATABASE_URL; skipped when unset
```

`/health/live` checks process liveness. `/health/ready` checks `SELECT 1` and
requires Alembic head `0019_neon_operational_indexes`.

The delivery excludes `__pycache__`, `*.pyc`, `.pytest_cache` and `.ruff_cache`. SEC raw
payloads, normalized facts, lineage, restatements and metric history remain
unchanged and append-only.
