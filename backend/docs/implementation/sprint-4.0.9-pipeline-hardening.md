# Sprint 4.0.9 — Financial Data Pipeline Hardening

## Implemented

### SEC transport resilience
- Bounded retries for HTTP 429 and transient 5xx responses.
- Bounded retries for timeout and transport errors.
- Supports `Retry-After` in seconds or HTTP-date form.
- HTTP 403 fails fast with an actionable User-Agent/access-policy message.
- SEC response errors retain status code and retryability metadata.
- Per-process request spacing remains conservative; it is not a distributed rate limiter.

### Persistent response cache
- Added `sec_provider_cache` and Alembic revision `0005_sec_provider_cache`.
- Company Facts response bodies are cached by CIK with configurable TTL.
- Cached payloads retain response hash and original text.
- Expired entries are refreshed; raw Company Facts payloads remain separately preserved in `sec_raw_company_facts`.

### Import idempotency and concurrency
- Replaced select-then-insert checks with PostgreSQL `INSERT ... ON CONFLICT DO NOTHING`.
- Raw payloads, reported facts, normalized facts and lineage now rely on database uniqueness constraints for concurrent import safety.
- Cache refresh uses an atomic PostgreSQL upsert.\n- Database read transactions are committed before SEC network I/O to avoid holding DB connections while waiting on the provider.
- Decimal observations must be finite; invalid values are skipped instead of persisted.

### Configuration
- Added `SEC_MAX_ATTEMPTS`, `SEC_RETRY_BASE_SECONDS`, `SEC_RETRY_MAX_SECONDS`, and `SEC_COMPANY_FACTS_CACHE_TTL_SECONDS`.
- Added validation for retry and cache settings.

## Validation

- Unit suite: 64 tests.
- Python compilation: passed.
- FastAPI import and route registration: passed.
- Alembic offline SQL generation through revision 0005: passed.
- Live PostgreSQL migration and SEC provider calls: not run in this environment.
- Ruff: not installed in this environment.

## Remaining known limitations

1. SEC request throttling is process-local. Multi-worker production must use a shared limiter or a single ingestion worker.
2. Company Facts is a non-dimensional aggregate feed; custom taxonomy tags and dimensional segment facts require filing-level XBRL processing.
3. `AS_KNOWN_AT` currently has date-level filing precision in the fact model.
4. Cash-flow CAPEX sign normalization remains an explicit, versioned mapping task; no blanket absolute-value conversion was introduced.
5. Cache refresh and raw ingestion share the database transaction; for high-volume operation, move provider fetch and import into a durable background job with explicit job state and dead-letter handling.
6. PostgreSQL `ON CONFLICT` behavior has been generated and unit-covered indirectly, but requires a real PostgreSQL integration test before production.

## Operational runbook

1. Set a real `SEC_USER_AGENT` including a monitored contact address.
2. Set retry/cache settings appropriate to the deployment.
3. Start PostgreSQL and apply `alembic upgrade head`.
4. Verify that revision `0005_sec_provider_cache` is present.
5. Register and SEC-verify a company and ticker.
6. Trigger Company Facts import twice; the second run should reuse the cache while unique constraints prevent duplicate fact records.
7. Expire the cache row or wait for TTL, trigger again, and verify that a changed payload is retained as a new immutable raw record.
8. Before multiple API workers are deployed, move SEC ingestion behind a shared rate limiter and job queue.
