# Sprint 4.0.3 — Asset Identity & SEC Integration

## Delivered

- Added `Company`, `Asset` and temporally valid `AssetIdentifier` persistence models.
- Added explicit identifier ownership: exactly one of company or asset.
- Added migration `0002_asset_identity`.
- Added company and asset creation endpoints and company/asset/identifier search.
- Added SEC ticker/exchange resolver using the official SEC ticker file.
- Added SEC submissions identity lookup by zero-padded CIK.
- Added unit tests for model registration, temporal constraints and ticker resolution.

## API

- `POST /api/v1/companies`
- `POST /api/v1/assets`
- `GET /api/v1/assets/search?q=MSFT`
- `GET /api/v1/sec/resolve/ticker?ticker=MSFT`
- `GET /api/v1/sec/verify-cik/0000789019`

SEC ticker resolution deliberately returns all candidates. It never auto-registers an ambiguous ticker. CIK verification returns the official company name, tickers, exchanges, SIC and fiscal year end for subsequent comparison.

## Important limitations

- SEC requests are throttled per process only. Multi-worker deployments need a shared limiter and persistent cache.
- The ticker file is an external snapshot; production ingestion should persist its raw payload, hash, retrieval timestamp and source metadata.
- No automatic registration from a SEC candidate is performed yet; verification and registration workflow will be completed with audit trail in a follow-up integration step.
- Identifier non-overlap across temporal ranges is not yet enforced at database level. Application-level validation and a PostgreSQL exclusion strategy are required before concurrent historical identifier writes.
- Authentication/authorization is not yet present; these endpoints are development-only and must not be exposed publicly.
- Real SEC network calls and PostgreSQL migration execution require the local environment and a valid SEC User-Agent contact.
- Added `POST /api/v1/identity/register-sec?ticker=MSFT`, which registers only a unique ticker candidate confirmed by the SEC submissions record and is idempotent for an existing matching CIK/ticker pair.
