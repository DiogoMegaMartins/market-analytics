# Sprint 4.1.7 — SEC Filing Document Ingestion & Extraction

## Delivered

- Added `SECFilingDocumentService` to download SEC EDGAR archive documents through the existing SEC client and retry/throttle policy.
- Enforces HTTPS, SEC host allow-list, EDGAR archive path, and a configurable-in-constructor byte ceiling (20 MiB default).
- Computes SHA-256 over original response bytes and records content type, byte count and extraction version.
- Added deterministic HTML/plain-text extraction and candidate section segmentation for Business, Risk Factors, MD&A and Financial Statements.
- Extraction output is explicitly a research candidate; it is not an approved fact, evidence conclusion or Business Quality score.

## Important limitations

- No persistent object storage/database archival or API endpoint was added in this sprint.
- No PDF/OCR, inline XBRL table reconstruction, exhibit processing or filing-specific custom section mapping.
- Section headings vary by form, issuer and filing layout; current patterns are conservative heuristics and may miss or misidentify sections.
- The document response is held in memory; production ingestion should stream to object storage with size limits and background jobs.
- SEC live download was not executed in validation; tests use deterministic fixtures.
- The SEC client limiter remains process-local.

## Validation

- `pytest -q`: 93 passed.
- `python -m compileall -q app`: passed.
- `alembic upgrade head --sql`: generated through revision 0007; no new migration required.
- FastAPI import: 25 routes.
