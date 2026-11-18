# Increment 5.19.0 — Portfolio valuation snapshot foundation

## Objective
Establish immutable, tenant-scoped and source-attributed dated valuations as the prerequisite for defensible performance calculations. TWR is deliberately not calculated from transaction data alone.

## Delivered
- New PostgreSQL table `portfolio_valuation_snapshots` with composite tenant FK, nonnegative values, ISO currency, constrained source, per-portfolio idempotency and date index.
- PostgreSQL trigger prevents UPDATE/DELETE (SQLSTATE 55000).
- POST and GET valuation endpoints with company authorization and portfolio ownership checks.
- Identical idempotent replay returns original snapshot; key reuse with changed content returns HTTP 409.
- Stores invested-asset market value and cash value separately; total value is their sum.
- Captures valuation date, source, methodology, optional source reference/notes, author and recorded timestamp.
- Unit and PostgreSQL integration tests cover validation, idempotency, tenant isolation and immutability.
- No frontend, performance calculations, provider ingestion, FX or production database operations.

## Performance semantics
DEPOSIT and WITHDRAWAL are external investor cash flows; BUY/SELL, dividend, interest, fees and taxes are portfolio events. Exact subperiod TWR needs valuation observations at external-flow boundaries. This increment stores valuation inputs but does not publish TWR/MWR until flow timing and valuation coverage contracts exist.

## Validation
CI is expected to run backend lint, migration chain, PostgreSQL migration/downgrade/upgrade, backend tests, frontend build and container image builds. Neon integration migrations remain manual-only.
