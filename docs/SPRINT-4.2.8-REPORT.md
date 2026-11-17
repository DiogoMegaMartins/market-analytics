# Sprint 4.2.8 — Observability, Monitoring & Operational Resilience

## Delivered

- Process-local, bounded-memory Prometheus metrics registry.
- HTTP request count and duration histogram using route templates (low cardinality).
- Server-generated `X-Request-ID` response header and JSON request log metadata.
- PostgreSQL pool metrics: size, checked-out, overflow and checked-in.
- SEC provider attempt, success, retry and failure counters.
- `/metrics` endpoint, hidden in staging/production unless a bearer token is configured; constant-time token comparison.
- Optional Prometheus + Grafana + node_exporter compose overlay.
- Prometheus scrape configuration and alert rules for 5xx rate, p95 latency, pool saturation, authentication failures, SEC retry spikes and backup failures/age.
- Grafana operations dashboard.
- PostgreSQL backup script emits atomic node_exporter textfile metrics when `BACKUP_METRICS_DIR` is configured.
- Restored the backup/restore scripts and operations runbook into the repository root (they had been nested in an old archive subdirectory).

## Validation

- `pytest -q`: 137 passed, 5 skipped.
- Python compilation: passed.
- Bash syntax checks: passed.
- Grafana dashboard JSON validation: passed.
- Prometheus, Grafana provisioning and Compose YAML parsing: passed.
- No new database migration.

## Limitations

- Metrics registry is process-local; use one worker per scrape target or replace it with shared/multiprocess instrumentation before horizontal scaling.
- Prometheus/Grafana were not started in this environment; no alert delivery was verified.
- PostgreSQL backup/restore was not run against a live database.
- Backup metrics require `BACKUP_METRICS_DIR` and node_exporter textfile collector configuration.
- No load test, pool exhaustion test or live SEC ingestion test was performed.
- The Next.js build was not part of this sprint's validation.
