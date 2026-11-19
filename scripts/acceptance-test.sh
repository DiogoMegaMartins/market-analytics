#!/usr/bin/env bash
set -Eeuo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000/api/v1}"
FRONTEND_BASE_URL="${FRONTEND_BASE_URL:-http://127.0.0.1:3000}"
API_ROOT="${API_BASE_URL%/api/v1}"
TMP_DIR="$(mktemp -d)"
COOKIE_JAR="$TMP_DIR/cookies.txt"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() { printf 'FAIL: %s\n' "$1" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$1"; }

status_code() {
  curl --silent --show-error --output "$TMP_DIR/body" --dump-header "$TMP_DIR/headers" \
    --write-out '%{http_code}' "$@"
}

code="$(status_code "$API_ROOT/health/live")"
[[ "$code" == "200" ]] || fail "API liveness returned HTTP $code"
grep -qi '^x-request-id: .\+' "$TMP_DIR/headers" || fail "API response did not include X-Request-ID"
grep -q '"status":"alive"' "$TMP_DIR/body" || fail "Unexpected liveness response"
pass "API liveness and request ID"

code="$(status_code "$API_ROOT/health/ready")"
[[ "$code" == "200" ]] || fail "API readiness returned HTTP $code (database/migrations may be unavailable)"
grep -q '"database":"connected"' "$TMP_DIR/body" || fail "Readiness did not confirm database connectivity"
pass "API readiness and database connectivity"

code="$(status_code "$API_BASE_URL/auth/me")"
[[ "$code" == "401" ]] || fail "Unauthenticated /auth/me should return 401, got HTTP $code"
pass "Unauthenticated API access is rejected"

code="$(status_code -X OPTIONS "$API_BASE_URL/auth/me" \
  -H 'Origin: http://localhost:3000' \
  -H 'Access-Control-Request-Method: GET' \
  -H 'Access-Control-Request-Headers: authorization,content-type')"
[[ "$code" == "200" ]] || fail "CORS preflight returned HTTP $code"
grep -qi '^access-control-allow-origin: http://localhost:3000' "$TMP_DIR/headers" \
  || fail "CORS did not allow the configured local frontend origin"
pass "CORS preflight for local frontend"

code="$(status_code "$FRONTEND_BASE_URL/")"
[[ "$code" == "200" ]] || fail "Frontend returned HTTP $code"
pass "Frontend HTTP response"

if [[ -n "${MA_ACCEPTANCE_EMAIL:-}" || -n "${MA_ACCEPTANCE_PASSWORD:-}" ]]; then
  [[ -n "${MA_ACCEPTANCE_EMAIL:-}" && -n "${MA_ACCEPTANCE_PASSWORD:-}" ]] \
    || fail "Set both MA_ACCEPTANCE_EMAIL and MA_ACCEPTANCE_PASSWORD"
  code="$(status_code -X POST "$API_BASE_URL/auth/token" \
    -H 'Content-Type: application/json' \
    -c "$COOKIE_JAR" \
    --data "$(python -c 'import json,os; print(json.dumps({"email":os.environ["MA_ACCEPTANCE_EMAIL"],"password":os.environ["MA_ACCEPTANCE_PASSWORD"]}))')")"
  [[ "$code" == "200" ]] || fail "Configured acceptance user could not log in (HTTP $code)"
  grep -q 'ma_access' "$COOKIE_JAR" || fail "Login did not issue the access cookie"
  pass "Configured test account can authenticate"

  code="$(status_code "$API_BASE_URL/auth/me" -b "$COOKIE_JAR")"
  [[ "$code" == "200" ]] || fail "Authenticated /auth/me returned HTTP $code"
  pass "Authenticated profile endpoint"

  if [[ -n "${MA_ACCEPTANCE_FOREIGN_COMPANY_ID:-}" ]]; then
    code="$(status_code "$API_BASE_URL/financial-data/companies/${MA_ACCEPTANCE_FOREIGN_COMPANY_ID}/facts" -b "$COOKIE_JAR")"
    [[ "$code" == "404" ]] || fail "Cross-tenant company access should return 404, got HTTP $code"
    pass "Cross-tenant company access is hidden (404)"
  else
    printf 'SKIP: cross-tenant HTTP test (MA_ACCEPTANCE_FOREIGN_COMPANY_ID not set)\n'
  fi
else
  printf 'SKIP: authenticated acceptance tests (MA_ACCEPTANCE_EMAIL/PASSWORD not set)\n'
fi

printf '\nAcceptance checks completed.\n'
