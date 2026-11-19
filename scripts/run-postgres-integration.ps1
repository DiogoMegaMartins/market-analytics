param([switch]$KeepDatabase)
$ErrorActionPreference = 'Stop'
function Invoke-Checked([string]$File, [string[]]$Arguments) {
  & $File @Arguments
  if ($LASTEXITCODE -ne 0) { throw "$File exited with code $LASTEXITCODE" }
}

$started = $false
try {
  Invoke-Checked 'docker' @('compose', '-f', 'docker-compose.postgres-test.yml', 'up', '-d', '--wait')
  $started = $true
  $env:DATABASE_URL = 'postgresql+asyncpg://market_test:market_test_only@127.0.0.1:55432/market_analytics_test'
  $env:DATABASE_URL_UNPOOLED = $env:DATABASE_URL
  $env:TEST_DATABASE_URL = $env:DATABASE_URL
  Push-Location backend
  Invoke-Checked 'python' @('-m', 'pip', 'install', '-e', '.[dev]')
  Invoke-Checked 'python' @('-c', 'import asyncpg, sqlalchemy; print(asyncpg.__version__, sqlalchemy.__version__)')
  Invoke-Checked 'alembic' @('upgrade', 'head')
  Invoke-Checked 'alembic' @('downgrade', '0018_point_in_time_contract')
  Invoke-Checked 'alembic' @('upgrade', 'head')
  # Full pytest runs the unit and opt-in PostgreSQL suites exactly once.
  Invoke-Checked 'python' @('-m', 'pytest', '-q')
  Invoke-Checked 'ruff' @('check', 'app', 'tests')
} finally {
  if ((Get-Location).Path -like '*\backend') { Pop-Location }
  if (-not $KeepDatabase) {
    & docker compose -f docker-compose.postgres-test.yml down -v
    if ($LASTEXITCODE -ne 0) { throw "docker compose cleanup exited with code $LASTEXITCODE" }
  }
}
