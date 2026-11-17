# Sprint 4.2.0 — SEC Evidence Extraction & Criterion Mapping

## Delivered

- Added `app/services/business_quality/evidence_extraction.py` with a versioned, deterministic retrieval layer (`bq-evidence-extraction-v1.0.0`).
- Exposed the Business Quality criterion catalogue from the existing scoring rubric. All 25 criteria have retrieval cues; the rubric remains the source of truth for dimension, label, weight and required status.
- Added a section extraction preview endpoint: `POST /api/v1/business-quality/document-sections/{section_id}/extract-candidates`.
- Added `GET /api/v1/business-quality/criteria` to inspect criteria and retrieval cues.
- Passage types are deliberately cautious: `RISK_DISCLOSURE`, `MANAGEMENT_ASSERTION`, `QUANTITATIVE_CLAIM`, and `NARRATIVE_CLAIM`.
- Potential conflicts are only heuristic flags for analyst review. No conflict is automatically resolved.
- Extraction preview is not persisted, verified, scored, or promoted to an approved evidence state. The existing evidence-candidate workflow remains the explicit persistence/review step.

## Safety and methodology boundaries

- Keyword matches are retrieval cues, not proof that a criterion is satisfied.
- Numeric language is labelled `QUANTITATIVE_CLAIM`, not `FACT`.
- Management statements remain management assertions, not independently verified facts.
- Risk disclosures remain risk disclosures; they are not treated as proof of realized harm.
- No AI-generated score or automated approval is introduced.
- Candidate extraction is bounded by a configurable maximum (1–200, default 50).

## Validation

- `pytest -q`: 103 passed.
- `compileall`: passed.
- FastAPI import: passed, 34 registered routes.
- Alembic offline SQL generation: passed through revision 0009; no schema migration was required.
- No live SEC retrieval or PostgreSQL integration migration was performed.

## Known limitations

- Retrieval uses deterministic English keyword cues and sentence splitting; it is not semantic search and can miss paraphrases or match irrelevant passages.
- Conflict detection is lexical and may generate false positives/negatives. It does not understand period, segment, scope, or accounting definitions.
- Current source locator uses approximate character offsets within the stored section, not original PDF page coordinates.
- Tables, inline XBRL, footnotes and document layout remain outside this extraction pass.
- Analyst authentication/RBAC is still required before public production use.

## Next recommended step

Build a human review workspace and persist extraction runs/candidates with extraction-version metadata, source offsets, criterion mapping, reviewer decisions, and explicit distinction between company assertions, reported metrics, third-party evidence, and analyst interpretation. Then evaluate precision/recall on a manually labelled sample before widening the rule set.
