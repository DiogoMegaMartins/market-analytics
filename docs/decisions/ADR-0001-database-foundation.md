# ADR-0001: PostgreSQL and asynchronous SQLAlchemy foundation

- Status: Accepted
- Date: 2026-11-10

## Context

Market Analytics requires relational integrity, immutable source and calculation
records, temporal identity, and transactional persistence. The initial repository
had a PostgreSQL container definition but no database runtime integration.

## Decision

- PostgreSQL 16 is the local and initial production relational database target.
- The API uses SQLAlchemy 2.x async sessions with the `asyncpg` driver.
- Alembic owns all schema changes; application startup never calls `create_all()`.
- The declarative metadata uses deterministic constraint naming conventions.
- UUID primary keys use PostgreSQL `gen_random_uuid()` server-side defaults.
- UTC-aware timestamps are the standard for shared timestamp mixins.
- Engine and session factory are created lazily, so importing model metadata does
  not establish a connection or require a running database.
- Liveness is independent of dependencies; readiness verifies PostgreSQL with
  `SELECT 1` and returns HTTP 503 when unavailable.

## Consequences

- Local development requires PostgreSQL and the declared `asyncpg` dependency.
- Domain models and their reviewed Alembic migrations must be introduced in
  subsequent implementation sprints.
- Production secrets and database credentials must be injected by the deployment
  environment; the Compose defaults are local-development credentials only.
