# Sprint 4.3.3 — LLM Provider Integration & Evaluation

## Delivered

- Added an optional OpenAI Responses API adapter using the existing HTTPX dependency.
- Added strict JSON Schema output mode and a provider-compatible schema normalizer.
- Added explicit configuration: `OPENAI_ENABLED`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, `OPENAI_TIMEOUT_SECONDS`, and `OPENAI_MAX_OUTPUT_TOKENS`.
- AI is disabled by default; enabling it requires an API key.
- Added authenticated, company-scoped `POST /api/v1/research/companies/{company_id}/copilot`.
- Reuses the deterministic SEC research brief and sends bounded evidence only.
- Provider calls set `store=false`; API credentials and provider error bodies are not logged or returned.
- Validates structured output and rejects citations not present in the request.
- Added mocked HTTP tests for request shape, strict schema, response parsing, and sanitized 429 handling.

## Safety and methodology boundaries

- The model cannot call tools or browse the web in this integration.
- Filing text is untrusted input and prompt-injection instructions are explicitly ignored.
- No evidence is treated as independently verified solely because the model repeats it.
- No model output can change deterministic metrics, Business Quality, valuation, or portfolio state.
- The endpoint is gated by the existing company membership policy; POST requires ANALYST or ADMIN.

## Validation limitations

- Provider calls were tested with HTTPX MockTransport, not with a live OpenAI account or API key.
- No live model quality, latency, token cost, data-retention, or regional-processing test was performed.
- Docker and live PostgreSQL acceptance tests remain environment-dependent.
- `store=false` is a request setting, not a substitute for reviewing provider terms and data controls.
- Passed OpenAI settings through the local Compose API service while keeping the feature disabled by default.
