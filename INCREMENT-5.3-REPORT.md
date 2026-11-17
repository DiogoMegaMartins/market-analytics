# Market Analytics — Increment 5.3 report

## Implemented

- Persistence contract now verifies that a committed original value survives
  both duplicate-fact `IntegrityError` and append-only update failure.
- Failed operations are isolated in `begin_nested()` savepoints; the session
  is reused after each failure, and confirmed rows remain visible.
- The service-level SEC import test still executes the real importer twice and
  verifies one raw payload, two accession observations, normalized facts and
  complete lineage.
- Added controlled concurrent same-payload imports to verify database-backed
  idempotency. A legitimate second accession remains distinct from a
  duplicate observation.
- The disposable PostgreSQL runner performs dependency import checks, empty
  database migration, 0019 downgrade/upgrade, one full pytest run, one Ruff
  run and cleanup with explicit exit-code checks.

## Test execution status

The corrected suite was prepared but not executed in this environment:

- Python 3.12+ is unavailable; the visible Windows Store alias is not a
  runnable interpreter.
- Docker/Docker Compose is unavailable, so PostgreSQL 16 could not be started.
- Therefore dependency installation, real migration, PostgreSQL pytest,
  transaction/persistence writes and Ruff were not completed here.
- No Neon remote access, migration or write was attempted. A connected plugin
  is not treated as application connectivity.

## Controlled execution

```powershell
.\scripts\run-postgres-integration.ps1
```

The script uses only local disposable credentials, destroys the test database
by default, and runs the integration suite once. Neon validation must remain a
separate authorized operation against a disposable branch; production
migrations and production data are out of scope.
