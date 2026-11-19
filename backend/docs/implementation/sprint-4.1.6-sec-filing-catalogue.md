# Sprint 4.1.6 — SEC Historical Filing Catalogue

## Scope
Added a reusable SEC EDGAR submissions catalogue. It indexes 10-K, 10-Q, 20-F and 6-K filing metadata, applies filing-date/form filters, fetches older submissions JSON shards linked by the SEC submissions index, constructs archive/document URLs, and computes a stable SHA-256 over key filing metadata.

## Important boundary
This sprint is a **metadata catalogue**, not a document evidence extractor. It does not download filing bodies, preserve raw filing bytes, parse sections, infer Business Quality scores, or prove historical public availability from filing date alone. Point-in-time eligibility still requires verified publication and availability timestamps under `PIT_EVIDENCE_1.0.0`.

## SEC policy
Requests use the existing SEC client, identifiable User-Agent, bounded retry and process-local throttle. Multi-worker rate coordination remains outstanding. The service only follows shard filenames returned by SEC and validates filename shape before requesting them.

## Validation
Unit tests cover recent filing parsing, date/form filtering, accession/document URL construction, malformed SEC arrays and historical shard collection. Live SEC calls and PostgreSQL persistence are not part of this sprint.
