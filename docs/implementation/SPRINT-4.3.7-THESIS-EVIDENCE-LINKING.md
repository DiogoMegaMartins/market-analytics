# Sprint 4.3.7 — Thesis Intelligence & Evidence Linking

## Objective
Make thesis assumptions auditable by connecting them to persisted source records, without turning evidence associations into automatic investment conclusions.

## Data model
`investment_thesis_evidence_links` stores one immutable link per record, attached to a thesis and exact immutable version, with an `assumption_id`, analyst relationship (`SUPPORTS`, `CONTRADICTS`, `QUALIFIES`), rationale, actor, and timestamp. Exactly one source target is allowed:
- `evidence_candidate_id` → `bq_evidence_candidates.id`
- `metric_result_id` → `financial_metric_results.id`

Database foreign keys protect source identity. CHECK constraints enforce exactly one target and the allowed relationship vocabulary. A database trigger prevents UPDATE/DELETE.

## API
- `POST /thesis/{thesis_id}/evidence-links` — creates a link to the current thesis version.
- `GET /thesis/{thesis_id}/evidence-links` — lists links across versions.
- `GET /thesis/{thesis_id}/intelligence` — summarizes links for the current version by assumption.

The API validates thesis ownership, assumption membership in the current version, source existence, company match, and (for financial metric links) exact `metric_id` match. Cross-company sources and mismatched financial metrics are rejected.

## Interpretation safeguards
- Documentary `CANDIDATE`, `VERIFIED`, `REJECTED`, and `SUPERSEDED` states remain distinct.
- Financial metric `CALCULATED` status is distinguished from all other statuses.
- Counts are descriptive. They are not evidence quality scores, causal conclusions, or thesis scores.
- No automatic invalidation, thesis status transition, Business Quality score change, Fair Value change, or recommendation change.
- Links are version-specific; a new thesis version does not silently inherit old links.

## Validation
- Unit tests cover route registration, model constraints, payload relationship validation, and model registry.
- Full backend test suite: 178 passed, 5 skipped.
- Python compile check: passed.
- Alembic offline SQL generation through revision `0013_thesis_evidence_links`: passed.
- Application import: passed; 62 routes registered.
- The five skipped tests require a live PostgreSQL integration environment. No live migration, database-trigger execution, HTTP tenant-isolation test, or Docker deployment was performed.

## Not included
No frontend UI, AI-generated evidence interpretation, automated evidence retrieval, or thesis scoring was added.
