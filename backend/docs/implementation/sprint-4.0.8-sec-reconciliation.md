# Sprint 4.0.8 — SEC Integration & Reconciliation

## Implemented

- Runtime reference catalog moved into `app/data/reference_financials_2024.json`.
- Reconciliation of persisted `NormalizedFinancialFact` rows against curated filing references.
- Endpoint `GET /api/v1/financial-data/companies/{company_id}/reconcile-reference?ticker=MSFT`.
- Explicit statuses for missing facts, value mismatches, unit/currency incompatibility, period mismatch, and ambiguous source/context.
- Ambiguous values are not silently resolved.
- Reference source and allowed tolerance are returned in the response.
- Added tests for matching, ambiguity, period mismatch and incompatible units.

## Important boundary

This sprint does not claim a live SEC import or a PostgreSQL end-to-end run. The endpoint reconciles data already imported and normalized in the database. Live provider access and DB integration still require a configured SEC User-Agent, network access and PostgreSQL.

## Operational runbook

1. Configure `SEC_USER_AGENT` with a real contact-bearing user agent.
2. Start PostgreSQL and apply migrations with `alembic upgrade head`.
3. Register and verify the company's SEC CIK and ticker.
4. Trigger SEC Company Facts import.
5. Call the reconciliation endpoint with the registered ticker.
6. Investigate any non-MATCH by accession, tag, unit, fiscal context, period and consolidated/segment scope.
