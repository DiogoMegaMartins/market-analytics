# Neon integration branch setup (Market Analytics 5.8.3)

## Scope and safety

This setup targets only the dedicated Neon branch `market-analytics-integration` in project `silent-star-01263357`, database `market-analytics-db`.

- Expected direct endpoint hostname: `ep-noisy-pond-bappn0py.c-8.eu-central-1.aws.neon.tech`
- The GitHub Actions job is manual (`workflow_dispatch`) only.
- It runs `alembic upgrade head` and PostgreSQL integration tests.
- It does not run a downgrade, does not import SEC facts, and does not write company/business data.
- Do not use a production URL or a pooled endpoint.

## Recommended: run the guarded GitHub Actions job

1. In Neon Console, select project `market-analytics`, branch `market-analytics-integration`, database `market-analytics-db`.
2. Copy the **direct** connection string for that branch. Use the async SQLAlchemy driver form (`postgresql+asyncpg://`) and require TLS (`ssl=require`). Do not use the pooler endpoint.
3. In GitHub, open the repository's **Settings → Secrets and variables → Actions**.
4. Create a repository secret named `NEON_INTEGRATION_DATABASE_URL` and paste the direct integration-branch URL into the secret value. Never paste the URL into chat, source files, logs, or commits.
5. Push this increment to the repository, open **Actions → Market Analytics CI → Run workflow**, and run it manually on the intended integration branch.
6. The `neon-integration-migrations` job checks the exact integration hostname before running. It then applies Alembic migrations through `0019_neon_operational_indexes`, verifies the head, and runs the PostgreSQL integration suite.

If the hostname guard fails, stop. Do not weaken the guard to make a different endpoint pass; verify the Neon branch and direct endpoint first.

## Alternative: manual SQL editor bootstrap

`ops/neon/integration-branch-bootstrap-0019.sql` is the offline SQL generated from the checked-in Alembic chain. If you choose to use it, first select the same integration branch and database in Neon SQL Editor. Execute the script once as a single transaction. Do not also run the workflow migration afterwards unless `alembic_version` confirms the database is already at the expected head.

The SQL creates the schema, indexes, functions, triggers, and Alembic version table. It contains no `DROP`, `TRUNCATE`, or business-row `DELETE` statements. It does not seed company rows or import SEC data.
