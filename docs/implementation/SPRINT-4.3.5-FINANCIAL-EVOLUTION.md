# Sprint 4.3.5 — Financial Evolution & Materiality

## Objective
Extend What Changed? with a deterministic comparison of persisted annual financial
metric runs, without allowing heuristic materiality to alter financial metrics,
Business Quality, Fair Value, or investment recommendations.

## API
`GET /api/v1/metrics/companies/{company_id}/evolution`

Required query parameters:
- `from_fiscal_year`
- `to_fiscal_year`

Optional:
- `materiality_threshold_pct` (default 10; allowed range greater than 0 through 1000)
- Comparison window limited to 15 fiscal years.

The endpoint selects the latest persisted `FinancialMetricRun` for each requested
endpoint fiscal year, then compares matching metric IDs and units. It returns run IDs,
engine versions, statuses, metric deltas, and materiality classifications.

## Materiality policy v1
- `MATERIAL`: absolute relative change meets or exceeds the configured threshold.
- `NON_MATERIAL`: absolute relative change is below the threshold.
- `REVIEW_REQUIRED`: unit mismatch or prior value is zero/negative.
- `NOT_ASSESSED`: missing metric, unavailable/invalid status, or non-finite value.

The default 10% threshold is an initial heuristic, not a validated accounting or
investment materiality standard. It is not sector-specific or metric-specific and
must be calibrated before being used in production workflows.

## Safeguards
- Values are compared only when both metric results have `CALCULATED` status.
- Units must match; no currency conversion is attempted.
- Negative/zero prior values are not assigned a relative percentage change.
- No causal interpretation or thesis status change is generated.
- No Business Quality score, fair value, or investment recommendation is modified.
- The endpoint inherits company-scoped authorization from the metrics router.

## Deliberately deferred
Thesis monitoring is not implemented in this sprint. The current repository does not
yet contain a persistent thesis/assumption model suitable for versioned point-in-time
comparison. The next increment should first define and persist thesis statements,
quantitative assumptions, invalidation conditions, evidence links, and analyst review
events before automatically flagging thesis changes.

## Known limitations
- Only the latest persisted metric run for each selected fiscal year is compared.
- Restated values can differ from the values known at the original reporting date.
- The endpoint compares two fiscal years, not a complete time series chart.
- A metric move can be economically immaterial even if it crosses the generic threshold.
- No sector-specific materiality or financial-statement reconciliation is performed here.

## Validation
Unit tests cover material/non-material changes, missing and unavailable metrics,
unit mismatch, non-positive base values, invalid period/threshold, and route scope.
Live PostgreSQL and tenant-isolation HTTP tests remain environment-dependent.
