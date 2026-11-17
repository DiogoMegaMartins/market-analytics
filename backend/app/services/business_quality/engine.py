from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

ENGINE_VERSION = "business-quality-v1.0.0"


class Dimension(StrEnum):
    BUSINESS_MODEL = "BUSINESS_MODEL"
    REVENUE_QUALITY = "REVENUE_QUALITY"
    COMPETITIVE_MOAT = "COMPETITIVE_MOAT"
    FINANCIAL_RESILIENCE = "FINANCIAL_RESILIENCE"
    MANAGEMENT_ALLOCATION = "MANAGEMENT_ALLOCATION"


@dataclass(frozen=True)
class Criterion:
    key: str
    label: str
    weight: Decimal
    required: bool = True


@dataclass(frozen=True)
class DimensionSpec:
    key: Dimension
    label: str
    criteria: tuple[Criterion, ...]


@dataclass(frozen=True)
class Observation:
    score: Decimal
    evidence_reference: str
    rationale: str
    confidence: str = "MEDIUM"


@dataclass(frozen=True)
class DimensionResult:
    dimension: str
    score: Decimal | None
    status: str
    completeness_pct: Decimal
    confidence: str
    missing_required: tuple[str, ...]


@dataclass(frozen=True)
class BusinessQualityResult:
    engine_version: str
    score: Decimal | None
    classification: str
    status: str
    completeness_pct: Decimal
    analysis_confidence: str
    dimensions: tuple[DimensionResult, ...]


# Initial expert rubric; weights are hypotheses and require empirical/sector calibration.
DIMENSIONS: tuple[DimensionSpec, ...] = (
    DimensionSpec(Dimension.BUSINESS_MODEL, "Business Model Quality", (
        Criterion("clarity", "Clareza do modelo", Decimal(20)),
        Criterion("demand_durability", "Durabilidade da procura", Decimal(25)),
        Criterion("unit_economics", "Economia unitária", Decimal(25)),
        Criterion("operating_leverage", "Alavancagem operacional", Decimal(15), False),
        Criterion("dependencies", "Dependências e resiliência", Decimal(15)),
    )),
    DimensionSpec(Dimension.REVENUE_QUALITY, "Revenue Quality", (
        Criterion("growth_quality", "Qualidade do crescimento", Decimal(20)),
        Criterion("recurrence", "Recorrência e previsibilidade", Decimal(25)),
        Criterion("customer_diversification", "Diversificação de clientes", Decimal(20)),
        Criterion("organic_growth", "Crescimento orgânico", Decimal(15), False),
        Criterion("cash_conversion", "Conversão em caixa", Decimal(20)),
    )),
    DimensionSpec(Dimension.COMPETITIVE_MOAT, "Competitive Moat", (
        Criterion("pricing_power", "Poder de preço", Decimal(25)),
        Criterion("switching_costs", "Custos de mudança", Decimal(20)),
        Criterion("scale_advantage", "Vantagem de escala/custos", Decimal(20)),
        Criterion("intangibles_network", "Intangíveis e efeitos de rede", Decimal(15), False),
        Criterion("durability", "Durabilidade da vantagem", Decimal(20)),
    )),
    DimensionSpec(Dimension.FINANCIAL_RESILIENCE, "Financial Resilience", (
        Criterion("leverage", "Endividamento", Decimal(25)),
        Criterion("liquidity", "Liquidez", Decimal(20)),
        Criterion("cashflow_resilience", "Resiliência dos cash flows", Decimal(25)),
        Criterion("profitability_stability", "Estabilidade da rentabilidade", Decimal(15)),
        Criterion("coverage_refinancing", "Cobertura e refinanciamento", Decimal(15)),
    )),
    DimensionSpec(Dimension.MANAGEMENT_ALLOCATION, "Management & Capital Allocation", (
        Criterion("capital_allocation", "Alocação de capital", Decimal(30)),
        Criterion("governance", "Governação e transparência", Decimal(25)),
        Criterion("alignment", "Alinhamento com acionistas", Decimal(20)),
        Criterion("execution", "Execução", Decimal(15)),
        Criterion("dilution", "Disciplina de diluição", Decimal(10), False),
    )),
)


def _confidence(values: list[str]) -> str:
    if not values or "LOW" in values:
        return "LOW"
    if "MEDIUM" in values:
        return "MEDIUM"
    return "HIGH"


def _classification(score: Decimal) -> str:
    if score >= 85:
        return "EXCELLENT"
    if score >= 70:
        return "STRONG"
    if score >= 55:
        return "AVERAGE"
    if score >= 40:
        return "WEAK"
    return "POOR"


def assess_business_quality(observations: Mapping[str, Observation]) -> BusinessQualityResult:
    """Score supplied, evidence-backed analyst observations; never infer missing scores."""
    dimensions: list[DimensionResult] = []
    for spec in DIMENSIONS:
        supplied: list[tuple[Criterion, Observation]] = []
        missing_required: list[str] = []
        covered_weight = Decimal(0)
        for criterion in spec.criteria:
            obs = observations.get(f"{spec.key.value}.{criterion.key}")
            if obs is None:
                if criterion.required:
                    missing_required.append(criterion.key)
                continue
            if not obs.evidence_reference.strip() or not obs.rationale.strip():
                raise ValueError(f"Evidence reference and rationale required: {spec.key}.{criterion.key}")
            if not Decimal(0) <= obs.score <= Decimal(100):
                raise ValueError(f"Score outside 0..100: {spec.key}.{criterion.key}")
            if obs.confidence not in {"LOW", "MEDIUM", "HIGH"}:
                raise ValueError(f"Invalid confidence: {spec.key}.{criterion.key}")
            supplied.append((criterion, obs))
            covered_weight += criterion.weight
        completeness = covered_weight.quantize(Decimal("0.01"))
        if missing_required:
            dimensions.append(DimensionResult(spec.key.value, None, "INSUFFICIENT_DATA", completeness,
                                              _confidence([o.confidence for _, o in supplied]),
                                              tuple(missing_required)))
            continue
        denominator = sum((c.weight for c, _ in supplied), Decimal(0))
        weighted = sum((c.weight * o.score for c, o in supplied), Decimal(0))
        score = (weighted / denominator).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        dimensions.append(DimensionResult(spec.key.value, score, "CALCULATED", completeness,
                                          _confidence([o.confidence for _, o in supplied]), ()))

    complete = all(d.score is not None for d in dimensions)
    overall_completeness = (sum((d.completeness_pct for d in dimensions), Decimal(0)) /
                            Decimal(len(dimensions))).quantize(Decimal("0.01"))
    confidence = _confidence([d.confidence for d in dimensions])
    if not complete:
        return BusinessQualityResult(ENGINE_VERSION, None, "UNAVAILABLE", "INSUFFICIENT_DATA",
                                     overall_completeness, confidence, tuple(dimensions))
    overall = (sum((d.score for d in dimensions if d.score is not None), Decimal(0)) /
               Decimal(len(dimensions))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return BusinessQualityResult(ENGINE_VERSION, overall, _classification(overall), "CALCULATED",
                                 overall_completeness, confidence, tuple(dimensions))
