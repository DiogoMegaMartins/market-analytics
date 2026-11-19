# AI Research & Investment Intelligence — v1 foundation

## Scope delivered in Sprint 4.3.1

The first increment is a deterministic, citation-first research brief assembled from SEC filing documents and sections that have already been ingested into the Business Quality evidence store.

Endpoint:

`GET /api/v1/research/companies/{company_id}/brief?as_of=YYYY-MM-DD&document_limit=50&max_passages=200`

The endpoint is company-membership protected by the existing company authorization dependency. It returns filing metadata, section-linked candidate passages, risk disclosures, management assertions, quantitative claims, and heuristic potential-conflict flags.

## Trust boundaries

- The service does not call an LLM or external model provider.
- It does not download filings; it uses previously persisted source documents and extracted sections.
- Passage retrieval is deterministic keyword matching using the existing Business Quality criterion catalogue.
- All extracted passages remain `UNVERIFIED_CANDIDATE`.
- Potential conflicts are heuristic opposing-language flags, not resolved contradictions.
- Management assertions are attributed as management statements, not independently verified facts.
- Quantitative claims are not reconciled automatically against financial facts, units, contexts, or reporting periods.
- No Business Quality score, fair value, investment recommendation, or portfolio action is generated.
- `as_of` filters by filing date, not exact public availability timestamp; the API makes this limitation explicit.

## Next increments

1. Add document ingestion adapters for supported SEC filing formats with robust section/page/paragraph locators.
2. Reconcile extracted quantitative statements to canonical financial facts and retain unmatched claims as unresolved.
3. Add explicit evidence relationships (`SUPPORTS`, `CONTRADICTS`, `QUALIFIES`, `CONTEXTUALIZES`) with reviewer workflow.
4. Introduce an optional LLM provider behind a strict structured-output interface, with citations required for every sourced assertion and prompt-injection isolation.
5. Evaluate extraction precision/recall and citation accuracy on a fixed, versioned filing corpus before enabling generated summaries.

## Example use

The brief can help an analyst navigate what a filing says about revenue quality, competitive position, financial resilience, management expectations, and disclosed risks. It is a research index, not a substitute for reading the filing or validating the underlying facts.
