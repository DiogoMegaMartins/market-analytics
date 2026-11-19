#!/usr/bin/env bash
set -Eeuo pipefail

: "${DATABASE_URL:?Set DATABASE_URL to the PostgreSQL async SQLAlchemy URL}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
command -v pg_dump >/dev/null || { echo "pg_dump is required" >&2; exit 1; }
command -v sha256sum >/dev/null || { echo "sha256sum is required" >&2; exit 1; }
[[ "$BACKUP_RETENTION_DAYS" =~ ^[0-9]+$ ]] || { echo "BACKUP_RETENTION_DAYS must be an integer" >&2; exit 1; }

record_backup_metric() {
  local success="$1"
  local metrics_dir="${BACKUP_METRICS_DIR:-}"
  [[ -n "$metrics_dir" ]] || return 0
  mkdir -p "$metrics_dir"
  local now last_success=0 tmp
  now="$(date +%s)"
  local metric_file="${metrics_dir%/}/market_analytics_backup.prom"
  if [[ -f "$metric_file" ]]; then
    last_success="$(awk '/market_analytics_backup_last_success_unixtime/ {print $2}' "$metric_file" | tail -1)"
    last_success="${last_success:-0}"
  fi
  if [[ "$success" == "1" ]]; then last_success="$now"; fi
  tmp="$(mktemp "${metrics_dir%/}/.backup-metrics.XXXXXX")"
  {
    echo '# HELP market_analytics_backup_last_run_success Whether the latest backup run succeeded.'
    echo '# TYPE market_analytics_backup_last_run_success gauge'
    echo "market_analytics_backup_last_run_success $success"
    echo '# HELP market_analytics_backup_last_run_unixtime Unix time of the latest backup attempt.'
    echo '# TYPE market_analytics_backup_last_run_unixtime gauge'
    echo "market_analytics_backup_last_run_unixtime $now"
    echo '# HELP market_analytics_backup_last_success_unixtime Unix time of the latest successful backup.'
    echo '# TYPE market_analytics_backup_last_success_unixtime gauge'
    echo "market_analytics_backup_last_success_unixtime $last_success"
  } > "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$metric_file"
}
trap 'record_backup_metric 0' ERR

# libpq understands postgresql://; SQLAlchemy's asyncpg driver suffix is not part of the URI scheme.
TMP_FILE=""
PGPASSFILE="$(mktemp)"
chmod 600 "$PGPASSFILE"
trap '[[ -z "$TMP_FILE" ]] || rm -f "$TMP_FILE"; rm -f "$PGPASSFILE"' EXIT
mapfile -d '' -t DB_CONFIG < <(python "$(dirname "$0")/pg-uri-to-env.py" "$DATABASE_URL" "$PGPASSFILE")
export PGPASSFILE
export PGHOST="${DB_CONFIG[0]}" PGPORT="${DB_CONFIG[1]}" PGUSER="${DB_CONFIG[2]}" PGDATABASE="${DB_CONFIG[3]}"
[[ -z "${DB_CONFIG[4]}" ]] || export PGSSLMODE="${DB_CONFIG[4]}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BASE="market-analytics-${STAMP}"
TMP_FILE="${BACKUP_DIR}/.${BASE}.dump.tmp"
APP_ENV="${APP_ENV:-development}"
RECIPIENT="${BACKUP_ENCRYPTION_RECIPIENT:-}"
if [[ "$APP_ENV" == "production" && -z "$RECIPIENT" ]]; then
  echo "BACKUP_ENCRYPTION_RECIPIENT is mandatory for production backups" >&2; exit 1
fi
if [[ -n "$RECIPIENT" ]]; then
  command -v age >/dev/null || { echo "age is required when backup encryption is enabled" >&2; exit 1; }
  FINAL_FILE="${BACKUP_DIR}/${BASE}.dump.age"
else
  FINAL_FILE="${BACKUP_DIR}/${BASE}.dump"
fi
pg_dump --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" --dbname="$PGDATABASE" --format=custom --no-owner --no-acl --file="$TMP_FILE"
pg_restore --list "$TMP_FILE" >/dev/null
if [[ -n "$RECIPIENT" ]]; then
  age --recipient "$RECIPIENT" --output "$FINAL_FILE" "$TMP_FILE"
  rm -f "$TMP_FILE"
else
  mv "$TMP_FILE" "$FINAL_FILE"
fi
chmod 600 "$FINAL_FILE"
HASH="$(sha256sum "$FINAL_FILE" | awk '{print $1}')"
PG_DUMP_VERSION="$(pg_dump --version | sed 's/"/\\"/g')"
MANIFEST_FILE="${FINAL_FILE%.dump*}.manifest.json"
python - "$FINAL_FILE" "$MANIFEST_FILE" "$HASH" "$PG_DUMP_VERSION" <<'PY'
import json, os, sys
from datetime import datetime, timezone
path, manifest_path, digest, version = sys.argv[1:]
manifest = {
    "created_at": datetime.now(timezone.utc).isoformat(),
    "file": os.path.basename(path),
    "sha256": digest,
    "size_bytes": os.path.getsize(path),
    "format": "postgresql-custom",
    "pg_dump_version": version,
}
with open(manifest_path, "x", encoding="utf-8") as handle:
    json.dump(manifest, handle, indent=2)
    handle.write("\n")
os.chmod(manifest_path, 0o600)
PY
find "$BACKUP_DIR" -type f \( -name 'market-analytics-*.dump' -o -name 'market-analytics-*.dump.age' \) -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete
find "$BACKUP_DIR" -type f -name 'market-analytics-*.manifest.json' -mtime "+${BACKUP_RETENTION_DAYS}" -delete
record_backup_metric 1
trap - ERR
printf 'Backup created: %s\nSHA-256: %s\n' "$FINAL_FILE" "$HASH"
