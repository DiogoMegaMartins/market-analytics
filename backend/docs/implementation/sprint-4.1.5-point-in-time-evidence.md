# Sprint 4.1.5 — Historical Dataset & Point-in-Time Evidence

## Delivered

- Added a deterministic point-in-time evidence eligibility policy (`PIT_EVIDENCE_1.0.0`).
- Evidence records retain criterion key, source identity/URL, publication time, availability time, archive capture time, content hash and source type.
- Evidence published or available after the assessment cutoff is excluded.
- Missing publication/availability timestamps are marked `UNVERIFIABLE_AVAILABILITY_DATE`; they are never assumed eligible.
- Naive timestamps and duplicate evidence identifiers are rejected.
- A reproducible manifest records cutoff, policy version, eligible IDs, exclusions and source provenance.

## Important limitation

This sprint adds a reusable validation/manifest layer, not an automated historical evidence collector or a fully persisted dataset UI. The caller must supply trustworthy `published_at` and `available_at` values. `captured_at` alone does not prove that information was public at the historical cutoff. SEC filing `filed_at`/acceptance timestamps can support availability for filings; web pages without reliable publication/archive timestamps remain unverifiable. No historical company scores are fabricated.

## Evaluation policy

- The assessment cutoff is timezone-aware.
- Both publication and availability timestamps must be at or before the cutoff.
- Missing timestamps are excluded with an explicit reason.
- Content hashes support integrity checks but do not establish source truth.
- This is a point-in-time evidence gate, not proof against survivorship bias, look-ahead bias, or predictive validity.
