# Sprint 4.1.8 — Evidence Persistence & Traceability

## Delivered
- Alembic revision 0008 creates source-document, extracted-section and evidence-candidate tables.
- Original SEC document bytes are persisted with SHA-256, accession, form, filing/publication dates, URL, content type and extraction version.
- Extracted sections are persisted with section key, sequence, extraction method and content hash.
- Evidence candidates link company → source document → section and criterion; each passage is hashed and carries a locator/rationale.
- Review workflow supports VERIFIED, REJECTED and SUPERSEDED; creator cannot review own candidate.
- API enforces official SEC HTTPS URL prefix, base64 validity and 20 MB maximum.

## Important limitations
- PostgreSQL BYTEA is an MVP persistence choice; versioned object storage is preferable for scale.
- API actor IDs are caller supplied; authentication/RBAC remains required before public deployment.
- No live SEC download or real PostgreSQL migration was executed in this sprint.
- Review state is mutable on the candidate row; a separate append-only evidence-review event ledger is a future hardening item.
