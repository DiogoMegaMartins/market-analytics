#!/usr/bin/env bash
set -Eeuo pipefail

: "${RESTORE_DATABASE_URL:?Set RESTORE_DATABASE_URL to the dedicated restore target}"
: "${RESTORE_CONFIRM_DATABASE:?Set RESTORE_CONFIRM_DATABASE to the exact target database name}"
: "${RESTORE_CONFIRM_HOST:?Set RESTORE_CONFIRM_HOST to the exact target database hostname}"
: "${ALLOW_DESTRUCTIVE_RESTORE:?Set ALLOW_DESTRUCTIVE_RESTORE=YES after confirming the target}"
: "${BACKUP_FILE:?Set BACKUP_FILE to a verified .dump backup}"
[[ "$ALLOW_DESTRUCTIVE_RESTORE" == "YES" ]] || { echo "Destructive restore not explicitly approved" >&2; exit 1; }
[[ "${APP_ENV:-development}" != "production" ]] || { echo "Refusing restore while APP_ENV=production" >&2; exit 1; }
[[ -f "$BACKUP_FILE" ]] || { echo "Backup file not found" >&2; exit 1; }
command -v pg_restore >/dev/null || { echo "pg_restore is required" >&2; exit 1; }
command -v sha256sum >/dev/null || { echo "sha256sum is required" >&2; exit 1; }

PGPASSFILE="$(mktemp)"
chmod 600 "$PGPASSFILE"
TMP_RESTORE=""
trap 'rm -f "$PGPASSFILE"; [[ -z "$TMP_RESTORE" ]] || rm -f "$TMP_RESTORE"' EXIT
mapfile -d '' -t DB_CONFIG < <(python "$(dirname "$0")/pg-uri-to-env.py" "$RESTORE_DATABASE_URL" "$PGPASSFILE")
export PGPASSFILE
export PGHOST="${DB_CONFIG[0]}" PGPORT="${DB_CONFIG[1]}" PGUSER="${DB_CONFIG[2]}" PGDATABASE="${DB_CONFIG[3]}"
[[ -z "${DB_CONFIG[4]}" ]] || export PGSSLMODE="${DB_CONFIG[4]}"
ACTUAL_DB="$PGDATABASE"
[[ -n "$ACTUAL_DB" && "$ACTUAL_DB" == "$RESTORE_CONFIRM_DATABASE" && "$PGHOST" == "$RESTORE_CONFIRM_HOST" ]] || {
  echo "Confirmation does not match target database host/name" >&2; exit 1;
}
MANIFEST="${BACKUP_FILE%.dump*}.manifest.json"
[[ -f "$MANIFEST" ]] || { echo "Backup manifest missing" >&2; exit 1; }
EXPECTED="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["sha256"])' "$MANIFEST")"
ACTUAL="$(sha256sum "$BACKUP_FILE" | awk '{print $1}')"
[[ "$EXPECTED" == "$ACTUAL" ]] || { echo "Backup SHA-256 mismatch" >&2; exit 1; }
RESTORE_INPUT="$BACKUP_FILE"
if [[ "$BACKUP_FILE" == *.age ]]; then
  : "${AGE_IDENTITY_FILE:?Set AGE_IDENTITY_FILE to the private age identity file}"
  command -v age >/dev/null || { echo "age is required to decrypt this backup" >&2; exit 1; }
  TMP_RESTORE="$(mktemp)"
  chmod 600 "$TMP_RESTORE"
  age --decrypt --identity "$AGE_IDENTITY_FILE" --output "$TMP_RESTORE" "$BACKUP_FILE"
  RESTORE_INPUT="$TMP_RESTORE"
fi
pg_restore --list "$RESTORE_INPUT" >/dev/null
printf 'Restoring backup into %s/%s. Existing objects may be dropped.\n' "$PGHOST" "$ACTUAL_DB"
pg_restore --host="$PGHOST" --port="$PGPORT" --username="$PGUSER" --dbname="$PGDATABASE" --clean --if-exists --no-owner --no-acl --exit-on-error "$RESTORE_INPUT"
echo "Restore command completed. Run application-level verification before promoting the target."
