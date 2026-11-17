# Observability & Monitoring

Status: instrumentation and example monitoring stack are implemented; external alert delivery and production deployment are not configured by this repository.

## API metrics

The API exposes Prometheus text format at `GET /metrics`.

- In development/test, the endpoint is available without a token.
- In staging/production, set `METRICS_TOKEN` to a high-entropy secret. The endpoint returns 404 when no token is configured and requires `Authorization: Bearer <token>` when configured.
- Create `ops/prometheus/secrets/metrics-token` containing the same token, with restrictive filesystem permissions. This file is ignored by Git.
- Do not expose `/metrics` publicly. Restrict it to the monitoring network or an authenticated scrape path.

Metrics include request count by HTTP method, route template and status; bounded request-duration histograms; PostgreSQL pool size/checked-out/overflow/checked-in; SEC request attempts, successes, retries and failures.

The registry is process-local and bounded-memory. It is suitable for one Uvicorn worker per scrape target. It is not an aggregation backend for multiple workers/replicas; use OpenTelemetry/Prometheus multiprocess instrumentation or scrape each worker independently before scaling horizontally. Route labels use route templates, not raw paths, to avoid high cardinality.

## Optional local Prometheus + Grafana

1. Start the API on the host at port 8000.
2. Export `METRICS_TOKEN` in the API environment and write the same value to `ops/prometheus/secrets/metrics-token` (chmod 600).
3. Set a unique `GRAFANA_ADMIN_PASSWORD`.
4. Run `docker compose -f docker-compose.observability.yml up -d`.
5. Open Prometheus at `http://localhost:9090` and Grafana at `http://localhost:3001`.

The compose overlay expects the API to be reachable as `host.docker.internal:8000`. It is an operational example, not a hardened internet-facing deployment. Put Grafana behind TLS and SSO/reverse proxy before shared use.

## Backup metrics

Set `BACKUP_METRICS_DIR` when invoking `scripts/backup-postgres.sh`, pointing it to `ops/backup-metrics` (or the node_exporter textfile collector directory). The script atomically writes:

- `market_analytics_backup_last_run_success` (1/0)
- `market_analytics_backup_last_run_unixtime`
- `market_analytics_backup_last_success_unixtime`

The optional compose overlay runs node_exporter with the textfile collector mounted from `ops/backup-metrics`. Schedule the backup with cron/systemd/Kubernetes or a managed scheduler; the application does not schedule it. Ensure the backup process can write to the directory and node_exporter can read it.

## Alerts and dashboard

- Alert rules: `ops/prometheus/alert-rules.yml`
- Scrape config: `ops/prometheus/prometheus.yml`
- Grafana dashboard: `ops/grafana/dashboards/market-analytics-operations.json`

Rules cover elevated 5xx rate, p95 latency, PostgreSQL pool saturation, SEC retries, failed backup attempts and backups older than 24 hours. Alert delivery requires an Alertmanager or managed Prometheus integration and must be configured separately.

## Important limitations

- Metrics reset when the API process restarts; Prometheus retains previously scraped samples.
- In-process counters do not prove SEC ingestion job completion unless the provider client is actually invoked.
- The backup metric is emitted only when `BACKUP_METRICS_DIR` is configured.
- No live Prometheus/Grafana deployment or alert notification was run in the development environment.
- No PostgreSQL pool exhaustion or load test was performed.
