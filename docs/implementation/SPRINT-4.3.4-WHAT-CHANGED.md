# Sprint 4.3.4 — What Changed?

## Objective
Provide a deterministic, date-bounded comparison of previously ingested SEC research
evidence and analyst-entered Business Quality assessments.

## API
`GET /api/v1/research/companies/{company_id}/what-changed?from_date=YYYY-MM-DD&to_date=YYYY-MM-DD`

Optional bounded parameters:
- `document_limit` (1–100, default 50)
- `max_passages` (1–1000, default 200)

The route inherits company-scoped authorization from the Business Quality router.
It returns newly ingested filings, evidence candidates newly retrieved or no longer
retrieved, summary count deltas, and the latest Business Quality assessment at each
cutoff date.

## Methodology and safeguards
- Both filing snapshots are built using the existing filing-date `as_of` policy.
- Business Quality comparisons use the latest stored assessment created on or before
  each cutoff. Scores are read-only and never recalculated or modified.
- Dimension deltas are shown only where both assessments contain finite numeric scores.
- A passage that is no longer retrieved is not treated as a removed risk.
- A newly retrieved passage is a candidate, not a verified fact.
- No causal explanation, fair value change, or investment recommendation is generated.
- Every result requires analyst review.
- Filing date is not treated as exact public availability time; look-ahead limitations
  remain when filing-time precision is unavailable.

## Known limitations
- This version compares the set of ingested documents available at request time, not
  an immutable historical ingestion snapshot. A document imported later can appear in
  an older filing-date comparison if its filed date is before the cutoff.
- Evidence retrieval is keyword-based and can miss relevant passages or change with
  retrieval rules. The report identifies this limitation explicitly.
- Business Quality assessments are analyst-entered snapshots; differences may reflect
  methodology, analyst judgment, or new evidence.
- The feature does not yet compare full financial metric series, valuation scenarios,
  market prices, or thesis-breaker events.

## Validation
Unit tests cover new filings, newly retrieved evidence, passage retrieval changes,
Business Quality dimension deltas, missing assessments, no-change cases, invalid date
ranges, and route registration. Live PostgreSQL and multi-tenant HTTP validation remain
environment-dependent.
