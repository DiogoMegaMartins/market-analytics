#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
: "${DATABASE_URL:=postgresql+asyncpg://market:market_dev_password@localhost:5432/market_analytics}"
: "${SECRET_KEY:=local-verification-secret-key-change-this-please-123456}"
export DATABASE_URL SECRET_KEY APP_ENV="${APP_ENV:-test}" APP_DEBUG="false"
export TEST_DATABASE_URL="${TEST_DATABASE_URL:-$DATABASE_URL}"

command -v python >/dev/null || { echo "python is required" >&2; exit 1; }
command -v npm >/dev/null || { echo "npm is required for frontend verification" >&2; exit 1; }

printf '\n== Backend: install ==\n'
python -m pip install -e "$ROOT/backend[dev]"

printf '\n== Backend: migrations ==\n'
(
  cd "$ROOT/backend"
  alembic upgrade head
  alembic current
  pytest -q
)

printf '\n== Frontend: install, typecheck, build ==\n'
(
  cd "$ROOT/frontend"
  npm install --no-audit --no-fund
  npm run typecheck
  npm run build
)

printf '\nVerification completed. PostgreSQL tests run only when TEST_DATABASE_URL points to a migrated test database.\n'
