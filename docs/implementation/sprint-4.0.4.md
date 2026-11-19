# Sprint 4.0.4 — Financial Data Pipeline

## Implemented

- SEC Company Facts endpoint client with CIK normalization, raw response preservation and SHA-256 payload hash.
- Immutable raw payload table `sec_raw_company_facts`.
- Reported fact table `financial_facts` with taxonomy/tag, exact unit, optional currency, value as `NUMERIC(38,10)`, fiscal period, form, accession, filed date, frame and retrieval timestamp.
- Initial US-GAAP mapping for revenue, operating income, net income, operating cash flow and property/plant/equipment capex. Alternative tags are ordered and never summed.
- Normalized reported facts and direct source lineage.
- Conservative period classifier for instant, annual, quarterly, YTD and unknown periods.
- Resolution policies `LATEST_RESTATED` and `AS_KNOWN_AT`; the latter requires a cutoff and excludes observations without a filing date.
- API to import Company Facts for an asset with a verified CIK and API to retrieve resolved reported facts.
- PostgreSQL append-only triggers for raw payloads, facts, normalized facts and lineage edges.

## API

- `POST /api/v1/financial-data/assets/{asset_id}/import/sec-company-facts`
- `GET /api/v1/financial-data/companies/{company_id}/facts?policy=LATEST_RESTATED`
- `GET /api/v1/financial-data/companies/{company_id}/facts?policy=AS_KNOWN_AT&as_known_at=2024-12-31`

## Deliberate limitations

- Only selected standard `us-gaap` tags are mapped. Custom company tags and dimensional facts are not imported.
- No YTD-to-quarter or Q4 derivation is performed yet. Reported facts are retained as reported; derivation must be a separate versioned step with multi-source lineage.
- `available_at` currently records retrieval time. SEC Company Facts observations expose a filing date but not a precise public-availability timestamp in this payload. `AS_KNOWN_AT` therefore uses `filed_at` at date precision and must not be interpreted as intraday point-in-time accuracy.
- The period classifier is deliberately conservative and is not a full fiscal-calendar resolver.
- CAPEX is stored using the provider-reported sign. No absolute-value conversion is applied.
- Import currently executes synchronously and sequentially. Production should queue large imports, use bounded batch operations and handle concurrent unique-key conflicts explicitly.
- SEC rate limiting is process-local. Multi-worker deployments need a shared limiter and provider-wide quota governance.
- A raw payload hash is unique per CIK; a repeat import of identical content reuses the existing raw record and skips duplicate facts.

## Validation

- Unit and existing tests: 25 passed.
- Python compileall: passed.
- Alembic offline SQL generation through revision `0003_sec_financial_data`: passed.
- Live SEC call and live PostgreSQL migration were not run in this environment.
