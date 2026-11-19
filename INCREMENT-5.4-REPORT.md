# Market Analytics — Increment 5.4 report

## Transaction fix

`test_sec_persistence_contract.py` now keeps one explicit main transaction
through setup, duplicate-fact failure, restatement insertion, append-only
failure and post-failure assertions. Only the two expected failures use
`session.begin_nested()` savepoints. The test verifies the original value,
both legitimate records, lineage and confirmed data after each rollback.

## SEC import coverage

The real `SECCompanyFactsImportService` tests cover initial import, second
idempotent import, concurrent same-payload imports, raw payload uniqueness,
distinct accession numbers, restatements, normalized facts and lineage.
Fixtures are isolated to the disposable PostgreSQL database and cleaned up.

## PostgreSQL execution result

The required runner was invoked:

```text
scripts/run-postgres-integration.ps1
```

Execution stopped before database startup because Docker is not installed on
this host (`docker` command not found). Therefore the following are **not
claimed as completed**: Python dependency installation, asyncpg validation,
PostgreSQL 16 startup, empty-database migrations, version 0019 verification,
downgrade/upgrade, pytest, Ruff, transaction writes or cleanup verification.

Python is also unavailable as a runnable Python 3.12+ interpreter, so the
suite cannot be executed independently on this host.

## Neon status

No production migration or remote write was attempted. No Neon URL or
credential was used. Plugin availability is not application connectivity;
project access, authenticated PostgreSQL connection, migrations and read/write
tests remain unverified.

## Next action

Install Docker Desktop and Python 3.12+, then run the disposable runner. Only
after it succeeds should a separately authorized disposable Neon branch be
validated using direct/unpooled migration URL and pooled application URL.
