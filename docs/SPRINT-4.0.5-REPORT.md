# Sprint 4.0.5 — Financial Metrics Engine & Data Quality

## Delivered

- Decimal-based pure metric calculators: revenue growth, operating margin, net margin,
  OCF margin, FCF and FCF margin; CAGR helper.
- Explicit statuses for calculated, unavailable and invalid results.
- CAPEX sign convention is not guessed; negative CAPEX blocks FCF.
- Initial quality rules for duplicate metric candidates, unit/currency/fiscal-year
  mismatches and negative CAPEX.
- Versioned metric runs and immutable metric result/lineage/finding records.
- Annual metrics API and latest-run history API.
- Quarter derivation Q2/Q3/Q4 from YTD/FY observations with two-source lineage.
- Alembic revision `0004_financial_metrics_quality`.

## API

- `POST /api/v1/metrics/companies/{company_id}/annual/{fiscal_year}`
- `GET /api/v1/metrics/companies/{company_id}/annual/{fiscal_year}/history`
- `POST /api/v1/metrics/companies/{company_id}/derive-quarters/{fiscal_year}`

## Validation

- 37 automated tests pass.
- Python compilation passes.
- Alembic offline SQL generation succeeds through revision 0004.
- Real PostgreSQL migration and end-to-end SEC ingestion remain unverified in this environment.
- Ruff was not installed in the execution environment.

## Known limitations

- Gross profit tag mapping is not yet included, so gross margin is unavailable.
- Quarterly metrics are not yet calculated; this sprint only derives quarterly facts.
- Quarter derivation currently uses latest available inputs and does not accept an
  `AS_KNOWN_AT` cutoff.
- Annual metric quality checks are an initial rule set, not a complete accounting
  validation framework.
- SEC filing date precision remains date-only; publication timestamp precision is not
  available in the current fact schema.
- CAPEX source sign normalization needs a reviewed, versioned mapping policy.
- No sector-specific metrics are included yet.
