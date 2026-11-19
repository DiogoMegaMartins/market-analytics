# Sprint 4.4.0 — Thesis Monitoring & Alerts

## Delivered

- `POST /api/v1/thesis/{thesis_id}/monitor` evaluates the latest persisted metric run (or the requested fiscal year) against the current immutable thesis version.
- A deterministic threshold breach creates a `THRESHOLD_BREACH` alert. A material-change alert is created when a calculated metric changes by at least 20% from the latest persisted run for the immediately preceding available fiscal year and matching unit. The denominator is the absolute prior value; a non-zero value emerging from zero is treated as unbounded/material. Missing, uncalculated, incompatible-unit and non-finite values do not produce a material-change alert.
- Detection is idempotent for thesis/version/assumption/metric-run/type. New alerts start as `PENDING`; `PATCH /api/v1/thesis/{thesis_id}/alerts/{alert_id}` permits `PENDING → REVIEWED`, `PENDING → RESOLVED`, and `REVIEWED → RESOLVED`. Resolved alerts are terminal.
- `GET /api/v1/thesis/{thesis_id}/alerts` returns alert details and append-only status history. Each monitoring execution is also recorded in thesis event history.
- The thesis dashboard can initiate monitoring and review/resolve alerts.
- Alembic migration `0014_thesis_monitoring_alerts` adds the persistence and immutable event log.

## Safety and interpretation

Threshold conditions are only the explicit conditions in the current thesis version. Materiality uses a fixed 20% relative-change rule for this increment; it is a configurable product policy in a future iteration, not a statistically calibrated threshold. Alerts request human review. They never modify thesis status, decisions, assumptions, or valuations. Detection only runs when the monitoring endpoint is called; this release does not include a scheduler, push delivery, or background worker.

## Validation and limitations

Pure deterministic material-change, model-registration, route-registration and status-input cases are covered by `backend/tests/unit/test_thesis_monitoring.py`. The backend suite passed with 182 tests and 5 PostgreSQL integration tests skipped because `TEST_DATABASE_URL` is not configured. Frontend typecheck and production build passed. Alembic can identify migration `0014_thesis_monitoring_alerts` as the current head, but migration execution and live authenticated API/database behavior remain unverified because PostgreSQL is unavailable.

Monitoring is currently initiated through the API/UI and is not scheduled automatically after each metric ingestion. The endpoint selects the latest run by fiscal year and creation time; historical source corrections and market-price monitoring are outside this release. Alert-event audit is append-only at the database trigger layer; alert rows retain mutable current state and each transition is separately preserved. A background scheduler/worker and notification delivery remain future work.
