# Sprint 4.3.0 — Integration & Acceptance Test Harness

## Objective

Turn the existing local deployment profile and CI database coverage into a repeatable acceptance procedure, without treating static checks as proof of a live deployment.

## Delivered

- Added `scripts/acceptance-test.sh`.
- Added `docs/testing/acceptance-testing.md` with local Compose and disposable test-account instructions.
- Updated README and deployment documentation with the extended verification procedure.
- Reused the existing CI PostgreSQL service and integration tests; no database schema change or migration was needed.

## Acceptance checks

The script verifies:

1. API liveness and server-generated `X-Request-ID`.
2. API readiness and PostgreSQL connectivity.
3. Unauthenticated `/auth/me` returns HTTP 401.
4. CORS preflight permits the configured local frontend origin.
5. Frontend root returns HTTP 200.
6. Optional: a disposable user can authenticate and read `/auth/me`.
7. Optional: a disposable user receives HTTP 404 when requesting financial facts for a company belonging exclusively to another test user.

## Validation in this execution environment

- Backend unit suite: 137 passed, 5 skipped.
- PostgreSQL driver `asyncpg` unavailable in the current runtime.
- Docker and PostgreSQL command-line/server tools unavailable.
- Therefore no live Compose startup, actual migration against PostgreSQL, authenticated HTTP flow, tenant-isolation HTTP request, backup/restore drill, Grafana/Prometheus launch, or load test was performed.
- The CI workflow is configured to provision PostgreSQL 16, run Alembic migrations, execute the integration suite with `TEST_DATABASE_URL`, run API health checks, and build both images. Its success must be confirmed by a GitHub Actions run on the target repository; local inspection is not evidence of a completed CI run.

## No schema changes

No Alembic migration was added. The current database migration head remains `0011_auth_security`.

## Exit criteria for a true live acceptance

- Successful CI run against PostgreSQL 16 with zero unexpected skips.
- Successful Compose startup with all four services healthy/completed.
- Successful authenticated and cross-tenant HTTP acceptance using disposable accounts.
- Recorded successful backup and isolated restore, including duration and integrity verification.
- Verified metrics scraping and alert delivery to a configured receiver.
- Load test with documented concurrency, latency percentiles, error rate and database pool utilization.
