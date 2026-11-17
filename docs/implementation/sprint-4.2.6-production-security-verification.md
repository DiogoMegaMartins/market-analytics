# Sprint 4.2.6 — Production Security Verification Coverage

## Scope

This sprint adds repeatable security checks rather than claiming a production deployment. It strengthens production CORS configuration and extends real-PostgreSQL tenant authorization coverage.

## Changes

- Integration tests create two companies and a user with membership in only one company.
- The test confirms access to the member company and a non-disclosing HTTP 404 for another company.
- The test also resolves a candidate by resource ID and confirms that a cross-tenant resource cannot be accessed even when the caller omits `company_id` from the URL.
- Reviewer permissions are tested against assessment creation and evidence review routes; Analyst/Reviewer/Admin write policy remains explicit.
- Staging/production settings require at least one explicit HTTPS CORS origin. Wildcard origins, HTTP origins, path-bearing origins, wildcard subdomains and URL credentials are rejected.
- CI already provisions PostgreSQL 16, applies Alembic migrations, sets `TEST_DATABASE_URL`, and runs all integration tests.

## Validation in the current execution environment

- `pytest -q`: 131 passed, 5 skipped.
- `python -m compileall -q app tests`: passed.
- `alembic upgrade head --sql`: generated successfully through revision `0011_auth_security`.
- FastAPI import: passed; 47 routes registered.
- Frontend typecheck/build: not run because `frontend/node_modules` is absent and dependency installation is not available in this execution.
- PostgreSQL integration tests: skipped locally because `TEST_DATABASE_URL` is not configured and no live PostgreSQL service is available. CI is configured to execute them against PostgreSQL 16; that remote CI result has not been observed here.

## Operational instructions

Run from the repository root with PostgreSQL 16 available:

```bash
docker compose up -d db
export TEST_DATABASE_URL="postgresql+asyncpg://market:market_dev_password@localhost:5432/market_analytics"
export DATABASE_URL="$TEST_DATABASE_URL"
cd backend
alembic upgrade head
pytest -q
```

For staging/production, configure `CORS_ALLOWED_ORIGINS` as a comma-separated list of exact HTTPS origins, e.g. `https://app.example.com,https://research.example.com`. Do not include paths, credentials, wildcard origins or plain HTTP origins.

## Remaining limitations

- PostgreSQL integration results still need to be observed in the actual CI run or a local PostgreSQL 16 environment.
- Frontend typecheck and production build remain unverified in this environment.
- This is not a penetration test or an external security audit.
- Rate limiting is database-backed and may require operational tuning under high concurrency.
- Cookie domain, TLS termination, trusted proxy handling, backup/restore and secrets rotation must be configured for the actual deployment.
