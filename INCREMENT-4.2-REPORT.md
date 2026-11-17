# Market Analytics — Increment 4.2 technical report

## Corrections

- Production/staging configuration tests now provide explicit database URLs
  where required, including browser-cookie and HTTPS-origin tests.
- Health tests independently mock database ping and schema verification,
  covering unavailable connection, stale schema and ready responses.
- Added dependency import coverage for SQLAlchemy and asyncpg.
- Added migration-chain contract coverage through `0019_neon_operational_indexes`.
- `.gitignore` and packaging exclude `.ruff_cache`, `.pytest_cache`,
  `__pycache__` and `*.pyc`.
- Audited packaged `.env*` files: only example files are present; no real
  credentials or active Neon connection was included.
- Existing SEC data, lineage, restatements, normalized data and metric history
  remain untouched. No investment score was introduced.

## Test execution status

- Unit tests: prepared and attempted with `python -m pytest -q tests/unit`.
  Execution was blocked because this environment exposes only the Windows
  Store Python placeholder, not a runnable Python 3.12+ interpreter.
- Full pytest: not executable for the same environment limitation.
- Ruff: not executable because Python/Ruff is unavailable.
- PostgreSQL integration tests: not executed; `TEST_DATABASE_URL` was not
  supplied and no PostgreSQL service was authenticated.
- Neon remote tests: not executed. No Neon credentials were inferred, stored,
  or represented as an active connection.
- Migration clean-database upgrade/downgrade: not executed without a live
  PostgreSQL database; the complete Alembic chain is statically validated and
  the 0019 migration remains reversible.

## Reproduction in a provisioned environment

```powershell
cd backend
python --version                 # Python 3.12+
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check app tests
$env:TEST_DATABASE_URL = 'postgresql+asyncpg://...'
alembic upgrade head
python -m pytest -q tests/integration
```

Only a user-provided `TEST_DATABASE_URL` may be used for PostgreSQL/Neon
validation. A successful local/static run must not be described as an active
Neon connection.
