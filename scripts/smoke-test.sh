#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:3000}"

check_url() {
  local label="$1" url="$2"
  local status
  status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --max-time 8 "$url")"
  if [[ "$status" != 2* ]]; then
    echo "FAIL: $label returned HTTP $status ($url)" >&2
    return 1
  fi
  printf 'PASS: %s (HTTP %s)\n' "$label" "$status"
}

command -v curl >/dev/null || { echo "curl is required" >&2; exit 1; }
check_url "API liveness" "${API_BASE_URL%/}/health/live"
check_url "API readiness (database connectivity)" "${API_BASE_URL%/}/health/ready"
check_url "Frontend root" "${FRONTEND_URL%/}/"
