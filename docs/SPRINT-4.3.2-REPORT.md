# Sprint 4.3.2 — AI Research Copilot Contract

## Delivered

- Provider-neutral `ResearchModel` protocol with explicit dependency injection.
- Bounded research question and evidence context.
- Stable citation IDs derived from source document, section, locator, and passage.
- Explicit untrusted-document / prompt-injection instruction boundary.
- Strict Pydantic structured-output schema; unexpected fields rejected.
- Citation whitelist validation; unknown or fabricated citation IDs rejected.
- Explicit insufficient-evidence abstention when the evidence set is empty.
- Output flags confirming that no investment recommendation or score/valuation modification was produced.
- Contract documentation and unit tests with a fake provider.

## Validation

- `pytest -q`: **147 passed, 5 skipped**.
- The five skipped tests require a live PostgreSQL integration environment.
- No external model provider was called; fake-provider tests validate orchestration and output controls only.

## Limitations

This sprint delivers a safety and integration contract, not a functioning hosted AI copilot. No provider credentials, model endpoint, data-processing agreement, retention configuration, cost controls, or production evaluation corpus are configured. Citations demonstrate source provenance, not factual truth. Analyst review remains mandatory.
