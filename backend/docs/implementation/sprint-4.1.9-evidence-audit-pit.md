# Sprint 4.1.9 — Evidence Review Audit & Point-in-Time Linking

## Delivered
- Added append-only `bq_evidence_review_events`, with event hashes linked to the prior event hash.
- Candidate creation writes the initial `CANDIDATE` event; review transitions append events and preserve the previous hash.
- Review endpoint locks the candidate row and permits only `CANDIDATE -> VERIFIED|REJECTED|SUPERSEDED`; creator self-review is rejected.
- Added immutable `bq_assessment_evidence_links` to snapshot eligibility decisions, cutoff, policy version and evidence hash.
- Point-in-time linking only considers `VERIFIED` evidence. Missing publication timestamps are unverifiable and excluded; publication after cutoff is excluded.

## Important constraints
- The hash chain is tamper-evident, not a cryptographic guarantee against a privileged database administrator rewriting the entire chain. Production should add database permissions/triggers and periodic external anchoring.
- Actor IDs remain client-supplied pending authentication/RBAC. Do not expose publicly yet.
- The point-in-time endpoint uses `published_at` as both publication and availability evidence. If it is absent, the item is excluded; `filed_at` is not silently substituted because date-only filing metadata may not prove intraday availability.
- Links are snapshots. If a source date is corrected, create a new assessment/link set rather than mutate old decisions.
- No live SEC or PostgreSQL integration was performed in this sprint.
