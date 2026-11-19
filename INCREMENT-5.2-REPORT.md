# Market Analytics — Increment 5.2 report

## Corrections

- Persistence tests now use an explicit main transaction for setup and
  `begin_nested()` only for recoverable constraint/append-only failures.
- After `IntegrityError` and append-only `DBAPIError`, the savepoint rolls back
  and the same session is reused for the restatement and verification steps.
- Added a service-level SEC import test that executes the same import twice,
  verifies one raw payload, two legitimate accession observations, two
  normalized facts and two lineage edges.
- Duplicate external facts are rejected by the database conflict path while a
  distinct accession/restatement remains preserved.
- The PowerShell runner now checks every external command exit code, verifies
  asyncpg/SQLAlchemy imports, performs upgrade → safe downgrade of 0019 →
  upgrade, runs full pytest once, and runs Ruff once.
- The PostgreSQL database remains disposable and is destroyed with `down -v`
  unless `-KeepDatabase` is explicitly supplied.

## Test status

The corrected tests and runner were packaged but could not be executed on this
host because Python 3.12+ and Docker are unavailable. Consequently, no local
PostgreSQL or Neon test is claimed as completed. No production data or real
credentials were used.

## Execution

```powershell
.\scripts\run-postgres-integration.ps1
```

This performs dependency installation, real PostgreSQL 16 startup, migrations
from an empty database, safe 0019 downgrade/upgrade, full pytest exactly once,
Ruff, and disposable database cleanup. Neon remote validation remains a
separate authenticated activity and is not implied by this local run.
