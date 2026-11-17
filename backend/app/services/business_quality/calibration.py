"""Offline sensitivity analysis for Business Quality dimension weights.

This module does not alter production assessments or claim statistical validation.
It quantifies how rankings move under explicitly supplied alternative hypotheses.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.services.business_quality.engine import Dimension

DIMENSION_KEYS = tuple(d.value for d in Dimension)


@dataclass(frozen=True)
class CalibrationCompany:
    company_key: str
    dimension_scores: Mapping[str, Decimal]


@dataclass(frozen=True)
class ScenarioResult:
    scenario: str
    scores: Mapping[str, Decimal]
    ranks: Mapping[str, int]


@dataclass(frozen=True)
class CompanySensitivity:
    company_key: str
    min_score: Decimal
    max_score: Decimal
    min_rank: int
    max_rank: int


@dataclass(frozen=True)
class CalibrationReport:
    scenarios: tuple[ScenarioResult, ...]
    sensitivity: tuple[CompanySensitivity, ...]


def run_weight_sensitivity(
    companies: Sequence[CalibrationCompany],
    scenarios: Mapping[str, Mapping[str, Decimal]],
) -> CalibrationReport:
    """Re-score complete dimension sets under alternative 100%-sum weight scenarios."""
    if not companies:
        raise ValueError("At least one company is required")
    if not scenarios:
        raise ValueError("At least one weight scenario is required")
    keys = [c.company_key.strip() for c in companies]
    if any(not key for key in keys) or len(set(keys)) != len(keys):
        raise ValueError("Company keys must be non-empty and unique")
    for company in companies:
        if set(company.dimension_scores) != set(DIMENSION_KEYS):
            raise ValueError(f"{company.company_key}: exactly five dimension scores are required")
        if any(not Decimal(0) <= Decimal(v) <= Decimal(100) for v in company.dimension_scores.values()):
            raise ValueError(f"{company.company_key}: dimension scores must be within 0..100")

    results: list[ScenarioResult] = []
    for name, weights in scenarios.items():
        if not name.strip() or set(weights) != set(DIMENSION_KEYS):
            raise ValueError("Each scenario must name and weight all five dimensions")
        normalized = {key: Decimal(value) for key, value in weights.items()}
        if any(value < 0 for value in normalized.values()):
            raise ValueError(f"Scenario {name}: negative weights are invalid")
        if sum(normalized.values(), Decimal(0)) != Decimal(100):
            raise ValueError(f"Scenario {name}: weights must sum to 100")
        scores = {
            c.company_key: (sum((Decimal(c.dimension_scores[k]) * normalized[k] for k in DIMENSION_KEYS), Decimal(0)) / Decimal(100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            for c in companies
        }
        ordered = sorted(scores, key=lambda key: (-scores[key], key))
        ranks = {key: index + 1 for index, key in enumerate(ordered)}
        results.append(ScenarioResult(name, scores, ranks))

    sensitivity = tuple(
        CompanySensitivity(
            company_key=c.company_key,
            min_score=min(r.scores[c.company_key] for r in results),
            max_score=max(r.scores[c.company_key] for r in results),
            min_rank=min(r.ranks[c.company_key] for r in results),
            max_rank=max(r.ranks[c.company_key] for r in results),
        ) for c in companies
    )
    return CalibrationReport(tuple(results), sensitivity)
