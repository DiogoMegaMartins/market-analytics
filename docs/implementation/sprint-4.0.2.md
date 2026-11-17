# Sprint 4.0.2 — Foundation & Database

## Implemented in this increment

- Environment configuration with explicit environment validation.
- Production/staging checks for secret strength and disabled debug mode.
- Async PostgreSQL engine, session factory, session dependency, ping and disposal.
- SQLAlchemy declarative base, UUID primary-key and UTC timestamp mixins.
- Alembic async environment and an intentionally empty baseline revision.
- Separate liveness and database readiness endpoints.
- Unit tests for configuration, metadata primitives and health endpoints.
- Backend setup and migration instructions.

## Verification

- `pytest -q`: 10 passed in the audit container.
- `python -m compileall -q app alembic tests`: passed.
- `alembic upgrade head --sql`: generated the baseline migration SQL.
- Ruff was not installed in the audit container; run `ruff check app tests` after
  installing the development extras.
- A live PostgreSQL connection and actual migration application were not verified
  because Docker/PostgreSQL and the `asyncpg` wheel were unavailable in the audit
  environment. `asyncpg` remains declared as a runtime dependency.

## Remaining before closing the sprint

1. Install the project with `pip install -e ".[dev]"` in the intended Python 3.12
   environment.
2. Start PostgreSQL and apply `alembic upgrade head` against a disposable local DB.
3. Verify `/health/ready` against both available and stopped PostgreSQL.
4. Run Ruff and frontend build in the normal development environment.
