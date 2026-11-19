# AI Research Copilot — Contract v1.0

## Scope

Sprint 4.3.2 introduces the provider-neutral boundary for a future LLM-backed research assistant.
It does not configure or call an external model provider and does not expose a public answer API.

## Flow

1. Build the deterministic filing brief from previously ingested SEC documents.
2. Submit the analyst question and a bounded set of candidate passages to `build_copilot_request`.
3. Each passage receives a stable citation identifier derived from its document, section, locator,
   and text. The source metadata and verification status remain attached.
4. An explicitly injected `ResearchModel` adapter may return structured output.
5. `validate_copilot_output` validates the response schema and rejects every citation identifier
   not present in the request evidence.
6. The validated result includes only citations actually referenced by claims.

## Guardrails

- Filing text is untrusted data, never executable instructions. The model instruction explicitly
  directs the provider to ignore embedded prompt-injection attempts.
- Every factual claim must include one or more request-scoped citation IDs.
- No evidence requires explicit abstention (`insufficient_evidence=true`).
- Management assertions remain attributed assertions, not independently verified facts.
- Candidate passages remain `UNVERIFIED_CANDIDATE`; citations establish provenance, not truth.
- Extra response fields are rejected. There are no score, fair-value, recommendation, or portfolio
  action fields in the output contract.
- The service does not update Business Quality, valuation, financial facts, or thesis records.
- Question, evidence count, passage length, claim count, and response sizes are bounded.

## Not delivered

- No OpenAI or other LLM API integration, key, network request, or model selection.
- No PDF/HTML filing ingestion enhancement or page-accurate extraction.
- No persistent conversation history or user-specific research chat.
- No quantitative-claim reconciliation against canonical facts.
- No model quality, hallucination, citation precision/recall, or prompt-injection benchmark.

## Before enabling a provider

Perform privacy and licensing review, configure data minimization and retention, select a supported
provider and region, implement timeout/retry/cost controls, add request/response audit metadata,
create a fixed evaluation corpus, and measure citation accuracy and abstention quality. Keep model
output advisory and require analyst review for material conclusions.
