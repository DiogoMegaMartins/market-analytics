import pytest
from pydantic import ValidationError

from app.services.research.copilot import (
    answer_research_question,
    build_copilot_request,
    validate_copilot_output,
)


def _brief():
    return {"evidence_candidates": [{
        "passage": "We expect organic revenue growth to improve.",
        "status": "UNVERIFIED_CANDIDATE", "criterion_key": "REVENUE_GROWTH",
        "passage_type": "MANAGEMENT_ASSERTION",
        "source": {"document_id": "d1", "section_id": "s1", "source_locator": "p1",
                   "accession_number": "0001", "source_url": "https://www.sec.gov/filing"},
    }]}


def test_build_request_bounds_evidence_and_marks_filing_text_untrusted():
    request = build_copilot_request("What did management say about growth?", _brief())
    assert len(request.evidence) == 1
    assert request.evidence[0].citation_id.startswith("ev_")
    assert "untrusted quoted data" in request.system_instructions
    assert "Every factual claim must cite" in request.system_instructions


def test_validate_output_accepts_only_supplied_citations():
    request = build_copilot_request("What did management say?", _brief())
    citation = request.evidence[0].citation_id
    result = validate_copilot_output({
        "answer": "Management expressed an expectation about growth.",
        "claims": [{"text": "Management expects growth to improve.", "citation_ids": [citation]}],
        "limitations": ["This is an attributed management assertion, not a verified forecast."],
        "insufficient_evidence": False,
    }, request)
    assert result["citations"][0]["citation_id"] == citation
    assert result["investment_recommendation_generated"] is False
    assert result["scores_or_valuation_modified"] is False


def test_validate_output_rejects_fabricated_citation():
    request = build_copilot_request("What did management say?", _brief())
    with pytest.raises(ValueError, match="unknown citation"):
        validate_copilot_output({
            "answer": "Unsupported.",
            "claims": [{"text": "Claim", "citation_ids": ["ev_fabricated"]}],
        }, request)


def test_empty_evidence_requires_abstention():
    request = build_copilot_request("What are the risks?", {"evidence_candidates": []})
    with pytest.raises(ValueError, match="insufficient evidence"):
        validate_copilot_output({
            "answer": "There is not enough source material.", "claims": [],
            "limitations": ["No filing passages were available."],
            "insufficient_evidence": False,
        }, request)


def test_question_is_bounded_and_extra_model_fields_are_rejected():
    with pytest.raises(ValidationError):
        build_copilot_request("x", _brief())
    request = build_copilot_request("Summarize the filing risks.", _brief())
    with pytest.raises(ValueError, match="Invalid structured"):
        validate_copilot_output({"answer": "OK", "claims": [], "score": 99}, request)


@pytest.mark.asyncio
async def test_orchestration_uses_injected_provider_and_validates_result():
    class FakeModel:
        async def generate_structured(self, request):
            return {"answer": "Insufficient evidence.", "claims": [],
                    "limitations": ["No matching passages."], "insufficient_evidence": True}

    result = await answer_research_question(
        question="What changed?", brief={"evidence_candidates": []}, model=FakeModel()
    )
    assert result["insufficient_evidence"] is True


def test_strict_response_schema_requires_all_object_fields_and_disallows_extras():
    from app.services.research.copilot import strict_response_schema

    schema = strict_response_schema()
    output = schema
    claim = schema["$defs"]["CopilotClaim"]
    assert set(output["required"]) == set(output["properties"])
    assert set(claim["required"]) == set(claim["properties"])
    assert output["additionalProperties"] is False
    assert claim["additionalProperties"] is False


@pytest.mark.asyncio
async def test_openai_responses_adapter_sends_strict_schema_and_parses_output():
    import httpx

    from app.services.research.openai_provider import OpenAIResponsesModel

    captured = {}

    async def handler(request):
        captured["body"] = __import__("json").loads(request.content)
        assert request.headers["Authorization"] == "Bearer test-secret"
        return httpx.Response(200, json={
            "status": "completed",
            "output_text": '{"answer":"Not enough evidence.","claims":[],"limitations":["No passages."],"insufficient_evidence":true}',
        })

    transport = httpx.MockTransport(handler)
    model = OpenAIResponsesModel(
        api_key="test-secret", model="test-model", transport=transport,
    )
    request = build_copilot_request("What changed?", {"evidence_candidates": []})
    result = await model.generate_structured(request)
    assert result["insufficient_evidence"] is True
    assert captured["body"]["store"] is False
    assert captured["body"]["text"]["format"]["strict"] is True
    assert captured["body"]["text"]["format"]["schema"] == request.response_schema


@pytest.mark.asyncio
async def test_openai_adapter_sanitizes_http_errors_and_marks_rate_limit_retryable():
    import httpx

    from app.services.research.openai_provider import OpenAIResponsesModel, ResearchProviderError

    async def handler(_request):
        return httpx.Response(429, json={"error": {"message": "sensitive provider details"}})

    model = OpenAIResponsesModel(
        api_key="test-secret", model="test-model", transport=httpx.MockTransport(handler),
    )
    request = build_copilot_request("What changed?", {"evidence_candidates": []})
    with pytest.raises(ResearchProviderError) as error:
        await model.generate_structured(request)
    assert error.value.retryable is True
    assert "sensitive provider details" not in str(error.value)
    assert error.value.status_code == 429


def test_openai_provider_is_disabled_by_default_and_requires_key_when_enabled():
    from pydantic import ValidationError

    from app.core.config import Settings

    settings = Settings(_env_file=None)
    assert settings.openai_enabled is False
    with pytest.raises(ValidationError, match="OPENAI_API_KEY is required"):
        Settings(_env_file=None, openai_enabled=True)
    enabled = Settings(_env_file=None, openai_enabled=True, openai_api_key="test-secret")
    assert enabled.openai_enabled is True
