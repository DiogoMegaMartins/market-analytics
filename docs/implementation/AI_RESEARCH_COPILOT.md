# AI Research Copilot

## Enablement

The Copilot is optional and disabled by default. Configure these environment variables on the API service:

```dotenv
OPENAI_ENABLED=true
OPENAI_API_KEY=<secret>
OPENAI_MODEL=gpt-5.5
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_TIMEOUT_SECONDS=45
OPENAI_MAX_OUTPUT_TOKENS=2500
```

Use a secret manager or deployment secret injection for `OPENAI_API_KEY`; do not commit it to `.env` files. The configured base URL must use HTTPS outside local development. Only set a custom base URL when the endpoint is trusted to receive the API credential and public filing excerpts.

## Request

`POST /api/v1/research/companies/{company_id}/copilot`

Requires a valid authenticated session and company membership with `ANALYST` or `ADMIN` role. Example body:

```json
{
  "question": "What are the main risks disclosed in the latest annual filing?",
  "document_limit": 30,
  "max_passages": 120
}
```

`as_of` is optional and uses the filing date cutoff. The endpoint uses only SEC filing sections already ingested into Market Analytics. It does not fetch new filings or perform general web research.

## Processing boundaries

1. The deterministic research brief selects candidate passages.
2. The Copilot request bounds the number and size of evidence passages.
3. The OpenAI Responses API is called with Structured Outputs and `store=false`.
4. Pydantic validates the response and the application checks every citation ID against the exact evidence supplied.
5. Unsupported citations or malformed output fail closed.

The integration does not enable tools, web search, or model-initiated actions. It does not write to the database and cannot modify financial facts, metrics, Business Quality assessments, valuation, portfolio positions, or investment decisions.

## Operational and privacy considerations

- Provider calls have a bounded timeout and output-token ceiling.
- 429 and 5xx responses are marked retryable, but this initial version does not automatically retry model calls.
- Provider error bodies, API credentials, and prompt content are not written to application logs.
- `store=false` requests non-storage for the response object; it is not a guarantee of zero retention or a substitute for reviewing the provider's current terms, data controls, regional processing, and contractual commitments.
- Only send public filing excerpts or other data approved by the organisation's privacy, legal, and security review.
- No live API-key or production-data test is included in the repository validation.
