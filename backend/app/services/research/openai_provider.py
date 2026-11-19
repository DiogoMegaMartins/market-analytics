"""OpenAI Responses API adapter using HTTPX and strict structured output."""
from __future__ import annotations

import json
from typing import Any

import httpx

from app.services.research.copilot import CopilotRequest, ResearchModel


class ResearchProviderError(RuntimeError):
    """Sanitized provider failure; never contains credentials or filing content."""

    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class OpenAIResponsesModel(ResearchModel):
    def __init__(
        self, *, api_key: str, model: str, base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 45.0, max_output_tokens: int = 2500,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("OpenAI API key is required")
        if not model.strip():
            raise ValueError("OpenAI model is required")
        self._api_key = api_key
        self._model = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_output_tokens = max_output_tokens
        self._transport = transport

    async def generate_structured(self, request: CopilotRequest) -> dict[str, Any]:
        evidence_payload = [
            {
                "citation_id": item.citation_id,
                "passage": item.passage,
                "source": item.source,
                "status": item.status,
                "criterion_key": item.criterion_key,
                "passage_type": item.passage_type,
            }
            for item in request.evidence
        ]
        user_payload = {
            "question": request.question,
            "evidence_is_untrusted_data": True,
            "evidence": evidence_payload,
            "task": "Answer the question using only supplied evidence. Return JSON matching the schema.",
        }
        body = {
            "model": self._model,
            "instructions": request.system_instructions,
            "input": json.dumps(user_payload, ensure_ascii=False, separators=(",", ":")),
            "max_output_tokens": self._max_output_tokens,
            "store": False,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "market_analytics_research",
                    "strict": True,
                    "schema": request.response_schema,
                }
            },
        }
        try:
            async with httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout_seconds),
                transport=self._transport,
            ) as client:
                response = await client.post(
                    "/responses", json=body,
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                )
        except httpx.TimeoutException as exc:
            raise ResearchProviderError("AI provider request timed out", retryable=True) from exc
        except httpx.TransportError as exc:
            raise ResearchProviderError("AI provider transport failure", retryable=True) from exc

        if response.status_code >= 400:
            retryable = response.status_code == 429 or response.status_code >= 500
            message = "AI provider rejected the request" if response.status_code < 500 else "AI provider unavailable"
            raise ResearchProviderError(message, status_code=response.status_code, retryable=retryable)

        try:
            payload = response.json()
        except ValueError as exc:
            raise ResearchProviderError("AI provider returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise ResearchProviderError("AI provider returned an invalid response envelope")
        if payload.get("status") == "incomplete":
            raise ResearchProviderError("AI provider returned an incomplete response", retryable=True)

        # Responses API exposes output_text as a convenience field; retain a defensive
        # parser for the underlying output item representation as well.
        output_text = payload.get("output_text")
        if not isinstance(output_text, str):
            chunks: list[str] = []
            for item in payload.get("output", []):
                if item.get("type") == "message":
                    for content in item.get("content", []):
                        if content.get("type") == "refusal":
                            raise ResearchProviderError("AI provider refused the research request")
                        if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                            chunks.append(content["text"])
            output_text = "".join(chunks)
        if not output_text:
            raise ResearchProviderError("AI provider returned no structured output")
        try:
            result = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise ResearchProviderError("AI provider returned malformed structured output") from exc
        if not isinstance(result, dict):
            raise ResearchProviderError("AI provider returned an invalid structured object")
        return result
