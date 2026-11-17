# Sprint 4.1.2 — Business Quality Review & Calibration Harness

## Scope delivered

- Added an offline, deterministic dimension-weight sensitivity utility.
- Supports named scenarios, requires all five dimensions and weights summing to exactly 100.
- Reports per-scenario scores/ranks and per-company score/rank ranges.
- Uses stable company-key tie-breaking so outputs are reproducible.
- Added unit tests for sensitivity, invalid weights and incomplete inputs.

## Methodology boundaries

This is a sensitivity-analysis harness, not empirical validation, analyst inter-rater testing, or sector calibration. It does not change stored assessments, production rubric weights, classifications, or investment decisions. Scenario weights are explicit hypotheses. Input dimension scores must already be complete and evidence-backed; missing dimensions are rejected rather than imputed.

## Not delivered

- No analyst approval workflow or identity-backed reviewer permissions.
- No empirical company reference dataset or historical point-in-time calibration.
- No sector-specific rubric or statistical validation against subsequent returns.
- No live PostgreSQL integration test.

## Next work

Create a controlled analyst review workflow, collect independently scored cases, measure inter-rater agreement, and only then consider rubric revisions under a new version. Keep old assessments immutable and comparable by rubric version.
