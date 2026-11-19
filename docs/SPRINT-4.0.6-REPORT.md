# Sprint 4.0.6 — Financial Metrics Validation & Historical Intelligence

## Delivered

- Added SEC `GrossProfit` mapping as `FIN.GROSS_PROFIT`.
- Added deterministic `FIN.GROSS_MARGIN` calculation and explicit input lineage.
- Bumped financial metrics engine version to `financial-metrics-v1.1`; prior runs remain identifiable.
- Added restatement comparison for repeated filings of the same canonical metric and economic period.
- Added configurable materiality threshold; the default 5% is explicitly a review heuristic, not an accounting standard.
- Added TTM aggregation for four consecutive standalone quarterly flow observations, with period, unit and currency validation.
- Added `AS_KNOWN_AT` cutoff support to quarterly derivation; observations without filing dates are excluded when a cutoff is requested.
- Added API endpoints for restatement inspection and TTM calculation.

## New API

- `GET /api/v1/financial-data/companies/{company_id}/restatements?metric_id=FIN.REVENUE&materiality_threshold=0.05`
- `GET /api/v1/metrics/companies/{company_id}/ttm?metric_id=FIN.REVENUE&as_known_at=2024-12-31`
- Existing quarter derivation endpoint now accepts `as_known_at`.

## Validation

- 44 automated tests pass.
- Python compilation passes.
- Alembic offline SQL generation succeeds through revision `0004`.
- No database schema change was required in this sprint.
- Live PostgreSQL and SEC integration remain unverified in this environment.
- Ruff is not installed in the execution environment.

## Known limitations

- Restatement detection is an inspection calculation and is not yet persisted as a dedicated immutable event table.
- Materiality is metric-agnostic; a 5% threshold must not be interpreted as a universal accounting materiality rule.
- TTM is available for additive flow metrics such as revenue, gross profit, operating income, net income, OCF and CAPEX. It is not appropriate for instant balance-sheet metrics.
- TTM requires four standalone quarterly observations; YTD observations must first be differenced into quarters.
- `AS_KNOWN_AT` is date-granular because filing timestamps are not represented at intraday precision.
- Fiscal quarter continuity is validated by date gaps (70–110 days); non-standard reporting calendars may require company-specific calendar metadata.
- Gross Profit availability depends on SEC standard-tag coverage and is not inferred from revenue minus cost of revenue in this sprint.
