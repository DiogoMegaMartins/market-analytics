from decimal import Decimal

import pytest

from app.services.business_quality.engine import DIMENSIONS, Observation, assess_business_quality


def complete_observations(score=80):
    return {
        f"{dimension.key.value}.{criterion.key}": Observation(
            Decimal(str(score)), "https://example.com/filing", "Analyst rationale", "HIGH"
        )
        for dimension in DIMENSIONS
        for criterion in dimension.criteria
        if criterion.required
    }


def test_complete_assessment_is_deterministic_and_separate_from_valuation():
    result = assess_business_quality(complete_observations())
    assert result.score == Decimal("80.00")
    assert result.classification == "STRONG"
    assert result.status == "CALCULATED"
    assert len(result.dimensions) == 5


def test_missing_required_evidence_does_not_become_zero():
    observations = complete_observations()
    observations.pop("COMPETITIVE_MOAT.pricing_power")
    result = assess_business_quality(observations)
    assert result.score is None
    moat = next(d for d in result.dimensions if d.dimension == "COMPETITIVE_MOAT")
    assert moat.score is None
    assert moat.status == "INSUFFICIENT_DATA"
    assert "pricing_power" in moat.missing_required


def test_optional_missing_reduces_completeness_but_not_score():
    observations = complete_observations()
    observations["BUSINESS_MODEL.operating_leverage"] = Observation(
        Decimal(80), "https://example.com/annual-report", "Optional criterion evidence", "HIGH"
    )
    result_without_optional = assess_business_quality(observations)
    observations.pop("BUSINESS_MODEL.operating_leverage")
    result = assess_business_quality(observations)
    assert result.score == result_without_optional.score
    business_model = next(d for d in result.dimensions if d.dimension == "BUSINESS_MODEL")
    assert business_model.completeness_pct == Decimal("85.00")


def test_invalid_score_or_missing_evidence_is_rejected():
    observations = complete_observations()
    observations["BUSINESS_MODEL.clarity"] = Observation(Decimal(101), "url", "why")
    with pytest.raises(ValueError, match="outside 0..100"):
        assess_business_quality(observations)
    observations["BUSINESS_MODEL.clarity"] = Observation(Decimal(50), "", "why")
    with pytest.raises(ValueError, match="Evidence reference"):
        assess_business_quality(observations)
