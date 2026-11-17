# Market Analytics — Increment 5 report

## Result

The project is prepared for authenticated Neon connectivity, but Neon
connectivity is **not complete or claimed** in this environment because
`DATABASE_URL`, `DATABASE_URL_UNPOOLED` and `TEST_DATABASE_URL` are unset.

## Implemented

- Application uses `DATABASE_URL`; optional direct `DATABASE_URL_UNPOOLED` is
  used by Alembic for migrations, preserving pooled/direct Neon separation.
- Connection-string normalization supports PostgreSQL/Neon URLs and TLS
  parameters without storing credentials.
- Added real PostgreSQL integration contract checks for migration head, indexes
  and foreign-key presence, gated by `TEST_DATABASE_URL`.
- Updated existing PostgreSQL head assertion to 0019.
- Preserved SEC raw data, normalized facts, lineage, restatements and metric
  history. No financial data was invented or rewritten.
- No global investment score was introduced.
- Packaging keeps `.env.example` files and excludes `.env` credentials,
  `__pycache__`, `*.pyc`, `.pytest_cache` and `.ruff_cache`.

## Required authenticated run

```powershell
cd backend
python -m pip install -e '.[dev]'
$env:DATABASE_URL = 'postgresql+asyncpg://...-pooler...?...ssl=require'
$env:DATABASE_URL_UNPOOLED = 'postgresql+asyncpg://...?...ssl=require'
$env:TEST_DATABASE_URL = $env:DATABASE_URL_UNPOOLED
alembic upgrade head
pytest -q
ruff check app tests
pytest -q tests/integration
```

Use a disposable Neon branch/database for writes and migration tests. The
direct/unpooled URL is required for Alembic; pooled traffic is appropriate for
the application. After the run, `/health/live` must return liveness and
`/health/ready` must report schema revision `0019_neon_operational_indexes`.

## Execution status in this environment

- Python dependency installation: not executed; no runnable Python 3.12+
  interpreter is installed (the available Windows Store alias is a placeholder).
- Pytest and Ruff: prepared but not executed for the same reason.
- PostgreSQL migration/read/write/constraint/lineage/idempotency tests: not
  executed because `TEST_DATABASE_URL` is unset.
- Neon TLS/authentication and health checks: not executed because no Neon URL
  or credentials were supplied.

No successful Neon connection, migration, write, or remote health check is
reported by this deliverable.
