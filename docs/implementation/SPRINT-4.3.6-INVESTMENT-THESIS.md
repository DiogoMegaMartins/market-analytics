# Sprint 4.3.6 — Investment Thesis Engine

## Objective
Create a versioned, user-owned investment thesis with explicit assumptions,
deterministic threshold evaluation, evidence references, and append-only analyst
decision history.

## Data model
- `investment_theses`: company, owner, title, status, current version pointer.
- `investment_thesis_versions`: immutable summary, rationale, assumptions, risks,
  evidence references, author, version number.
- `investment_thesis_events`: immutable deterministic evaluations and analyst decisions.

A PostgreSQL trigger prevents UPDATE/DELETE on thesis versions and events. The thesis
header remains mutable for its current version pointer and manually recorded status.

## API
- `POST /api/v1/thesis/companies/{company_id}/theses`
- `GET /api/v1/thesis/companies/{company_id}/theses`
- `GET /api/v1/thesis/{thesis_id}`
- `POST /api/v1/thesis/{thesis_id}/versions`
- `POST /api/v1/thesis/{thesis_id}/evaluate?fiscal_year=2024`
- `POST /api/v1/thesis/{thesis_id}/decisions`
- `GET /api/v1/thesis/{thesis_id}/events`

Theses are private to their owner; company ADMIN can inspect company theses.
The company-scoped authorization dependency still verifies membership. Writes require
ANALYST or ADMIN according to the existing route policy.

## Explicit invalidation assumptions
Each assumption contains:
- unique `assumption_id` and human-readable description
- canonical `metric_id`
- `condition` (`ABOVE` or `BELOW`)
- finite decimal threshold
- exact expected unit

Evaluation uses the latest persisted metric run for the requested fiscal year.
Only CALCULATED values with matching units are evaluated. Missing/unavailable data is
UNKNOWN; unit mismatch is REVIEW_REQUIRED. A threshold crossing is BREACH_CANDIDATE,
never automatic thesis invalidation.

## Analyst decisions
The analyst may record KEEP, REVISE, INVALIDATE, or ON_HOLD. These decisions are
stored as append-only events. Only explicit INVALIDATE changes thesis status to
INVALIDATED. REVISE requires a subsequent new version; the event itself does not
rewrite history.

## Safeguards and limitations
- The AI does not decide thesis status in this sprint.
- The evaluation engine is deterministic and does not infer causality.
- No missing metric is treated as a breach.
- The current implementation evaluates explicit numeric metric thresholds only;
  qualitative conditions require analyst review and are stored as narrative risks/
  evidence references, not automatically evaluated.
- Latest metric runs may contain restated values. Point-in-time metric-run selection
  and thesis backtesting are deferred.
- Company admin access is broader than owner access by design; all other users see
  only their own theses.
- Evaluation events are snapshots and are not recalculated retroactively.

## Migration
Alembic revision `0012_investment_thesis` follows `0011_auth_security`.
No migration has been run against a live PostgreSQL instance in this environment.

## Validation
Unit tests cover breach/no-breach, missing data, unavailable metrics, unit mismatch,
ABOVE conditions, empty assumptions, and route registration. Live database, HTTP
authorization, and PostgreSQL trigger behavior require integration validation.
