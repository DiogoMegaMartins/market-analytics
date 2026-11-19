# Market Analytics — Increment 5.1 report

## Implemented

- Added disposable PostgreSQL 16 Compose profile with `tmpfs` storage and no
  persistent volume: `docker-compose.postgres-test.yml`.
- Added `scripts/run-postgres-integration.ps1`, which starts PostgreSQL,
  installs `.[dev]`, runs Alembic to 0019, executes full pytest, Ruff and the
  PostgreSQL integration suite, then destroys the test database by default.
- Added real PostgreSQL contract coverage for migration head, indexes and
  foreign keys.
- Added isolated synthetic-fixture tests for SEC raw facts, normalized facts,
  Financial Fact Lineage, duplicate import idempotency, accession/restatement
  preservation, append-only protection and transaction rollback.
- Kept production SEC data untouched; fixtures are only created in the
  disposable test database and are cleaned up.
- No real credentials, Neon URLs, production data or global investment score
  were added.

## Execution status

The tests are prepared but were not executable on this host:

- Python 3.12+: unavailable; only the Windows Store placeholder exists.
- Docker Compose/PostgreSQL: unavailable; `docker` is not installed.
- asyncpg/SQLAlchemy installation: not executed because Python is unavailable.
- Alembic clean-database upgrade/downgrade: not executed because Docker/
  PostgreSQL is unavailable.
- Pytest and Ruff: not executed for the same reason.
- Neon remote tests: not executed; no Neon URL or credentials were used.

## Local execution

From the repository root, with Python 3.12+ and Docker Desktop installed:

```powershell
.\scripts\run-postgres-integration.ps1
```

For a manual authenticated Neon validation, provide a disposable Neon branch
through environment variables only:

```powershell
$env:DATABASE_URL = 'postgresql+asyncpg://...-pooler...?ssl=require'
$env:DATABASE_URL_UNPOOLED = 'postgresql+asyncpg://...?ssl=require'
$env:TEST_DATABASE_URL = $env:DATABASE_URL_UNPOOLED
cd backend
python -m pip install -e '.[dev]'
alembic upgrade head
python -m pytest -q
ruff check app tests
```

Use the direct/unpooled URL for Alembic and a disposable branch for writes.
Only after those commands succeed may the report state that Neon connectivity
was tested. This delivery makes no such claim.
