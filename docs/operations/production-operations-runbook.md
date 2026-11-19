# Production Operations & Recovery Runbook

Status: operational baseline for review; not evidence that production deployment or recovery has been exercised.

## 1. Required production configuration

Set secrets through the deployment secret manager, not a committed `.env` file. At minimum:

- `APP_ENV=production`, `APP_DEBUG=false`.
- `SECRET_KEY`: unique random value of at least 32 characters; rotate using a planned session invalidation window.
- `DATABASE_URL`: PostgreSQL TLS connection, with a dedicated least-privilege application role.
- `CORS_ALLOWED_ORIGINS`: exact HTTPS browser origins only.
- `TRUSTED_HOSTS`: exact API hostnames only, comma-separated; no wildcard.
- `SEC_USER_AGENT`: identifiable contact string for SEC access.
- `LOG_LEVEL=INFO`, `JSON_LOGS=true`.

Never put credentials, cookies, authorization headers, request bodies, or full connection strings in logs. The HTTP middleware logs method, path without query string, status, duration and a server-generated request ID.

## 2. Reverse proxy and client IPs

Terminate TLS at a managed ingress/reverse proxy. Configure the ASGI server to trust forwarded headers **only** from the exact proxy IP/CIDR ranges, e.g. Uvicorn `--proxy-headers --forwarded-allow-ips=<trusted-proxy-CIDRs>`. Do not use `*`. The application must not infer client IP from arbitrary `X-Forwarded-For` values. Restrict direct network access to the API so clients cannot bypass the trusted ingress.

## 3. PostgreSQL backups

`scripts/backup-postgres.sh` creates PostgreSQL custom-format dumps, validates the archive directory, writes a SHA-256 manifest, applies file permissions and prunes files older than `BACKUP_RETENTION_DAYS` (default 14).

Example development invocation:

```bash
export DATABASE_URL='postgresql+asyncpg://backup_user:password@db-host:5432/market_analytics'
export BACKUP_DIR=/secure/backups
export BACKUP_RETENTION_DAYS=14
./scripts/backup-postgres.sh
```

For production, `APP_ENV=production` requires `BACKUP_ENCRYPTION_RECIPIENT` and the `age` utility. Store the corresponding private identity separately in a secrets manager or offline recovery vault; never store it beside the backups. Copy encrypted backups and manifests to a separate account/region with object-lock or equivalent retention controls. A local backup on the same host is not a disaster-recovery strategy.

The script uses the PostgreSQL client utilities (`pg_dump`, `pg_restore`) and must be run with a client version compatible with the database server. Use a dedicated backup role with only the required read privileges. Set `BACKUP_METRICS_DIR` to the node_exporter textfile collector directory to publish backup success/failure and last-success timestamps to Prometheus.

## 4. Restore drill

Restore only into a disposable, isolated recovery database. The restore script refuses `APP_ENV=production`, requires an explicit `ALLOW_DESTRUCTIVE_RESTORE=YES`, requires the target database name to be repeated in `RESTORE_CONFIRM_DATABASE`, and verifies the backup manifest hash before restore.

```bash
export APP_ENV=staging
export RESTORE_DATABASE_URL='postgresql+asyncpg://restore_user:password@recovery-db:5432/market_analytics_restore'
export RESTORE_CONFIRM_DATABASE=market_analytics_restore
export RESTORE_CONFIRM_HOST=recovery-db
export ALLOW_DESTRUCTIVE_RESTORE=YES
export BACKUP_FILE=/secure/backups/market-analytics-<timestamp>.dump.age
export AGE_IDENTITY_FILE=/secure/recovery/backup-age-identity.txt
./scripts/restore-postgres.sh
```

After restore:

1. Run `alembic upgrade head` only if the recovery plan requires applying migrations beyond the backup point.
2. Verify row counts and foreign-key integrity for critical tables.
3. Start the API against the recovery database and check `/health/ready`.
4. Verify authentication, tenant isolation, document retrieval and an end-to-end Business Quality read.
5. Record recovery time and data-loss window. Do not promote the recovery database until the owner signs off.

A successful `pg_restore` command is not a completed restore drill. Perform scheduled restore exercises and record measured RTO/RPO.

## 5. Monitoring and incident response

- Liveness: `GET /health/live` (process responsiveness only).
- Readiness: `GET /health/ready` (database connectivity).
- Alert on sustained readiness failures, elevated 5xx rates, authentication throttling, SEC provider failures, database pool exhaustion and backup job failures.
- Correlate logs using `X-Request-ID`; do not log request payloads or secrets.
- Restrict log access and retention; security/audit logs may contain personal or operational metadata.
- On suspected credential compromise: revoke sessions, rotate affected secrets, preserve audit logs, and follow the incident response procedure.

## 6. Operational limits / outstanding work

- No live backup or restore has been executed in this development environment.
- No production metrics backend, alert delivery, Sentry or OpenTelemetry exporter is configured here.
- Backup encryption uses `age` only when explicitly configured; production mode requires a recipient.
- The application does not schedule backups itself. Run the script via a managed scheduler/backup service and monitor exit status.
- Define business-approved RPO/RTO, retention, geographic replication, key recovery, and privacy retention before production launch.
