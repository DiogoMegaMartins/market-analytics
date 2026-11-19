# Sprint 4.0.7 — End-to-End Financial Validation

## Objective

Add filing-backed regression references for three companies with different fiscal calendars and business models, and make financial fact reconciliation explicit and non-destructive.

## Reference set

Amounts are stored in full USD (not USD millions).

| Ticker | FY | Period end | Revenue | Gross profit | Operating income | Net income |
|---|---:|---|---:|---:|---:|---:|
| MSFT | 2024 | 2024-06-30 | 245,122,000,000 | 171,008,000,000 | 109,433,000,000 | 88,136,000,000 |
| AAPL | 2024 | 2024-09-28 | 391,035,000,000 | 180,683,000,000 | 123,216,000,000 | 93,736,000,000 |
| KO | 2024 | 2024-12-31 | 47,061,000,000 | 28,737,000,000 | 9,992,000,000 | 10,649,000,000 |

Sources:
- Microsoft 2024 Annual Report: https://www.microsoft.com/investor/reports/ar24/
- Apple 2024 Form 10-K: https://d18rn0p25nwr6d.cloudfront.net/CIK-0000320193/1e7e3da9-526f-477e-add2-b6ea6deb3d81.html
- Coca-Cola 2024 Q4 Earnings Release: https://www.coca-colacompany.com/content/dam/corporate/us/en/media-center/Coca-Cola%202024%20Q4%20Earnings%20Release_Full%20Release_2.11.25.pdf

Coca-Cola net income uses consolidated net income ($10,649m), not the amount attributable to shareowners ($10,631m), to align with the consolidated income-statement line.

## Implemented

- Curated reference fixture with CIK, fiscal year, exact period end, currency/unit and source citation.
- Pure reconciliation service with statuses MATCH, MISMATCH, MISSING, INCOMPATIBLE_UNIT and INCOMPATIBLE_PERIOD.
- Configurable absolute and relative tolerances.
- Regression tests for gross, operating and net margins across three distinct fiscal calendars.
- Reconciliation does not overwrite or normalize actual observations.

## Validation boundaries

This is a filing-backed regression baseline, not proof of a live SEC import. The execution environment has no confirmed live SEC/PostgreSQL integration in this sprint. Cash flow and CAPEX are intentionally omitted from this baseline until their statement values, taxonomy mapping and sign conventions are verified against each filing. A passing fixture test proves deterministic calculation against the curated reference, not that the ingestion pipeline fetched those facts correctly.

## Next validation work

1. Run SEC imports for the three CIKs in a configured environment.
2. Reconcile the imported normalized facts against this fixture, after explicit unit scaling.
3. Add cash flow and CAPEX references with filing-specific mapping notes.
4. Add database integration tests for raw payload, reported fact, normalized fact, metric run and lineage.
5. Resolve any differences by inspecting accession, tag, context, unit, fiscal period and accounting scope.
