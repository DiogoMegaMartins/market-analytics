# Research Intelligence

Estado: **implementação inicial disponível (Sprint 4.3.1)**.

`brief.py` agrega secções SEC previamente persistidas num brief determinístico, com citações por documento/secção, classificação de passagens e sinalização heurística de potenciais conflitos. Não chama modelos externos, não verifica a verdade das afirmações, não calcula scores e não produz recomendações de investimento.

Contrato, endpoint, limites e próximos incrementos: `docs/research/ai-research-intelligence-v1.md`.

## Research copilot contract (Sprint 4.3.2)

`copilot.py` defines a provider-neutral model adapter contract and a citation-constrained
structured-output validator. It bounds questions and evidence, assigns deterministic citation
IDs to retrieved passages, labels filing text as untrusted input, and rejects citations that
were not supplied to the model. It also requires explicit abstention when no evidence is
available and prohibits score, valuation, or recommendation outputs in the response contract.

No external model provider is configured or called by this sprint. A provider implementation
must be explicitly injected through `ResearchModel`; provider credentials, data-processing
terms, retention, region, rate limits, and evaluation remain deployment decisions. The current
brief still supplies only previously ingested filing passages and does not verify their claims.

## OpenAI Responses API integration

The optional HTTPX adapter in `openai_provider.py` calls the OpenAI Responses API
with Structured Outputs (`text.format.type=json_schema`, `strict=true`). It sends
only the bounded evidence selected by the research brief and sets `store=false`.
The API key is read from `OPENAI_API_KEY`; it is never returned or logged.

Enable explicitly with `OPENAI_ENABLED=true`, configure `OPENAI_MODEL`, and set a
secret API key in the runtime environment. The default is disabled. The protected
company-scoped endpoint is `POST /api/v1/research/companies/{company_id}/copilot`
with JSON `{ "question": "..." }`. It requires an authenticated company member
with ANALYST or ADMIN role under the existing company access policy.

Provider output is validated again by Pydantic and every claim citation must match
one of the evidence identifiers supplied in that request. Provider refusals,
timeouts, rate limits, incomplete output and malformed output fail closed. The
adapter does not enable web search or tools and does not alter financial metrics,
Business Quality scores, fair value or investment decisions.

The request uses `store=false`, but this is not a guarantee that no processing or
retention occurs under the provider's applicable terms and settings. Review current
provider data controls, contractual terms, jurisdiction, and any applicable privacy
and data-transfer requirements before production use. Do not send confidential or
personal data unless the relevant legal and security review permits it.
