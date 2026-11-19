# Market Analytics — Increment 4.1 technical report

## Delivered

- Production/staging configuration now requires an explicit `DATABASE_URL`.
- Remote PostgreSQL/Neon URLs must use TLS; `sslmode=require` is normalized to
  `ssl=require` for asyncpg.
- Production rejects the development secret, debug mode, invalid CORS and
  implicit/default database configuration.
- Root and backend `.env.example` files are identical and contain placeholders
  only.
- Alembic chain is explicit from the existing 0014 baseline through
  `0015_integration_readiness`, `0016_connection_hardening`,
  `0017_sec_preservation`, `0018_point_in_time_contract` and
  `0019_neon_operational_indexes`.
- Readiness checks both database connectivity and migration head 0019.
- Existing SEC, normalized facts, lineage, restatement and metric-history
  structures were not replaced or rewritten.
- No global investment score was introduced.
- Delivery packaging excludes `__pycache__`, `*.pyc` and `.pytest_cache`.

## Test classification

- Unit tests: `pytest -q tests/unit` — covers configuration, TLS, migration
  contract and existing domain behavior.
- PostgreSQL tests: `pytest -q tests/integration` — opt-in through
  `TEST_DATABASE_URL` and require a migrated disposable PostgreSQL database.
- Neon remote tests: not executed without a user-supplied Neon
  `TEST_DATABASE_URL`; no remote credentials were inferred or stored.

## Configuration

See `docs/NEON_SETUP.md`. For production, set `DATABASE_URL` explicitly to a
TLS-enabled Neon connection string, run `alembic upgrade head`, then verify
`/health/live` and `/health/ready`.
