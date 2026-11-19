# Sprint 4.1.3 — Analyst Review Workflow

## Scope

Adds an append-only review-event trail for immutable Business Quality assessments. Assessment content and score payloads are not edited by the workflow.

## State machine

- `DRAFT` → `SUBMITTED` (`SUBMIT`)
- `SUBMITTED` → `REVIEWED` (`REVIEW`)
- `REVIEWED` → `APPROVED` (`APPROVE`) or `REJECTED` (`REJECT`)
- `REJECTED` → `SUBMITTED` (`SUBMIT`) for a revised/re-submitted assessment workflow

Review and final decision actors must differ from the assessment's submitting analyst when an analyst ID is recorded. Approval/rejection requires a comment. Each transition is stored as a separate event; no event update/delete API exists. Assessment row locking serializes transition attempts.

## API

- `POST /api/v1/business-quality/assessments/{assessment_id}/review-events`
- `GET /api/v1/business-quality/assessments/{assessment_id}/review-events`

Actions: `SUBMIT`, `REVIEW`, `APPROVE`, `REJECT`. The first workflow state is `DRAFT`, inferred when no events exist.

## Important limitations

This is a workflow foundation, not production-grade authorization. `actor_id` is currently supplied by the caller because authentication/authorization is not yet integrated; it must not be trusted as identity in a public deployment. The same applies to analyst identity on assessment creation. A later identity/RBAC sprint must derive actors from authenticated principals, enforce reviewer permissions and tenant ownership, and prevent self-approval at the authorization layer. The workflow does not yet implement two-person quorum, delegation, or signed approvals.

An assessment is immutable; a correction should be represented by a new assessment linked to the prior one in a future revision. `REJECTED` permits re-submission of the same assessment in this prototype, which should be revisited when a formal revision model exists.
