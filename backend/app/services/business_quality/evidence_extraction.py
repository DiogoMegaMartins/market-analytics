"""Deterministic candidate extraction and criterion mapping for SEC filing text.

This module locates potentially relevant passages. It does not verify claims,
resolve truth, score criteria, or replace analyst review.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.services.business_quality.engine import DIMENSIONS

EXTRACTION_VERSION = "bq-evidence-extraction-v1.0.0"

# Keywords are retrieval cues, not proof that a criterion is satisfied.
_CRITERION_CUES: dict[str, tuple[str, ...]] = {
    "clarity": ("business model", "our business", "how we generate revenue", "operating model"),
    "demand_durability": ("demand", "customer demand", "long-term demand", "market demand", "secular trend"),
    "unit_economics": ("unit economics", "gross margin", "contribution margin", "customer acquisition cost"),
    "operating_leverage": ("operating leverage", "fixed costs", "incremental margin", "scale efficiencies"),
    "dependencies": ("key supplier", "single source", "supplier concentration", "dependency", "supply chain"),
    "growth_quality": ("organic growth", "revenue growth", "volume growth", "price increases", "acquisition-related growth"),
    "recurrence": ("recurring revenue", "subscription", "renewal rate", "remaining performance obligations", "backlog"),
    "customer_diversification": ("largest customer", "customer concentration", "top ten customers", "no single customer"),
    "organic_growth": ("organic growth", "constant currency", "excluding acquisitions", "comparable sales"),
    "cash_conversion": ("operating cash flow", "free cash flow", "cash conversion", "accounts receivable"),
    "pricing_power": ("pricing power", "price increases", "pricing actions", "ability to raise prices"),
    "switching_costs": ("switching costs", "customer retention", "customer churn", "cost to switch", "high switching"),
    "scale_advantage": ("economies of scale", "cost advantage", "scale advantage", "lowest-cost producer"),
    "intangibles_network": ("intellectual property", "patent portfolio", "brand strength", "network effects", "proprietary technology"),
    "durability": ("competitive advantage", "competitive position", "barriers to entry", "competitive moat", "market leadership"),
    "leverage": ("total debt", "net debt", "debt to ebitda", "leverage ratio", "borrowings"),
    "liquidity": ("cash and cash equivalents", "liquidity", "current assets", "current liabilities", "available credit"),
    "cashflow_resilience": ("cash flows", "operating cash flow", "cash generation", "cash flow volatility"),
    "profitability_stability": ("operating margin", "net margin", "profitability", "operating income", "earnings volatility"),
    "coverage_refinancing": ("interest coverage", "debt maturity", "refinancing", "covenant", "credit facility"),
    "capital_allocation": ("capital allocation", "share repurchases", "dividend", "acquisition", "return on invested capital"),
    "governance": ("corporate governance", "board of directors", "internal controls", "related party", "audit committee"),
    "alignment": ("insider ownership", "executive compensation", "shareholder interests", "long-term incentives"),
    "execution": ("strategic priorities", "implementation", "operational performance", "restructuring plan"),
    "dilution": ("share-based compensation", "stock-based compensation", "dilution", "shares outstanding"),
}

_RISK_CUES = ("risk", "could adversely", "may adversely", "uncertainty", "exposure", "vulnerable", "material weakness")
_MANAGEMENT_CUES = ("we believe", "we expect", "we intend", "our strategy", "we plan", "management believes")
_POSITIVE_CUES = ("increase", "improve", "growth", "strengthen", "expand", "higher", "reduced")
_NEGATIVE_CUES = ("decrease", "decline", "deteriorate", "weaken", "contract", "lower", "increased risk")
_NUMBER_RE = re.compile(r"(?:\$|€|£)?\b\d[\d,.]*(?:%|\s?million|\s?billion|\s?thousand)?\b", re.IGNORECASE)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])")


@dataclass(frozen=True)
class CriterionDefinition:
    criterion_key: str
    dimension: str
    label: str
    weight: str
    required: bool
    retrieval_cues: tuple[str, ...]


@dataclass(frozen=True)
class EvidencePassage:
    criterion_key: str
    dimension: str
    passage: str
    source_locator: str
    passage_type: str
    matched_cues: tuple[str, ...]
    rationale: str
    extraction_version: str = EXTRACTION_VERSION


def criterion_catalog() -> tuple[CriterionDefinition, ...]:
    """Return the engine rubric plus retrieval cues, preserving the rubric as source of truth."""
    rows: list[CriterionDefinition] = []
    for dimension in DIMENSIONS:
        for criterion in dimension.criteria:
            rows.append(CriterionDefinition(
                criterion_key=f"{dimension.key.value}.{criterion.key}",
                dimension=dimension.key.value,
                label=criterion.label,
                weight=str(criterion.weight),
                required=criterion.required,
                retrieval_cues=_CRITERION_CUES.get(criterion.key, ()),
            ))
    return tuple(rows)


def _passage_type(sentence: str) -> str:
    lowered = sentence.casefold()
    if any(cue in lowered for cue in _RISK_CUES):
        return "RISK_DISCLOSURE"
    if any(cue in lowered for cue in _MANAGEMENT_CUES):
        return "MANAGEMENT_ASSERTION"
    if _NUMBER_RE.search(sentence):
        return "QUANTITATIVE_CLAIM"
    return "NARRATIVE_CLAIM"


def _split_sentences(text: str) -> Iterable[tuple[int, str]]:
    """Yield approximate character offsets and trimmed sentences."""
    cursor = 0
    for raw in _SENTENCE_SPLIT.split(text):
        start = text.find(raw, cursor)
        if start < 0:
            start = cursor
        cursor = start + len(raw)
        sentence = raw.strip()
        if len(sentence) >= 35:
            yield start + (len(raw) - len(raw.lstrip())), sentence


def extract_evidence_candidates(
    text: str, *, section_key: str, max_candidates: int = 50,
) -> tuple[EvidencePassage, ...]:
    """Find sentences matching criterion retrieval cues; all results remain unverified candidates."""
    if not isinstance(text, str) or not text.strip():
        return ()
    if not 1 <= max_candidates <= 200:
        raise ValueError("max_candidates must be between 1 and 200")
    section = section_key.strip().upper()
    if not section:
        raise ValueError("section_key is required")

    definitions = criterion_catalog()
    results: list[EvidencePassage] = []
    seen: set[tuple[str, str]] = set()
    for offset, sentence in _split_sentences(text):
        lowered = sentence.casefold()
        for definition in definitions:
            cues = definition.retrieval_cues
            matched = tuple(cue for cue in cues if cue in lowered)
            if not matched:
                continue
            identity = (definition.criterion_key, sentence.casefold())
            if identity in seen:
                continue
            seen.add(identity)
            results.append(EvidencePassage(
                criterion_key=definition.criterion_key,
                dimension=definition.dimension,
                passage=sentence,
                source_locator=f"section:{section};char_start:{offset};char_end:{offset + len(sentence)}",
                passage_type=_passage_type(sentence),
                matched_cues=matched,
                rationale=("Keyword-based retrieval match only; analyst verification is required. "
                           "This passage is not a verified fact or a Business Quality score."),
            ))
            if len(results) >= max_candidates:
                return tuple(results)
    return tuple(results)


def detect_potential_conflicts(passages: Iterable[EvidencePassage]) -> tuple[dict, ...]:
    """Flag opposing directional language for analyst inspection; never resolve contradictions."""
    grouped: dict[str, list[EvidencePassage]] = {}
    for passage in passages:
        grouped.setdefault(passage.criterion_key, []).append(passage)
    conflicts: list[dict] = []
    for criterion, items in grouped.items():
        for index, left in enumerate(items):
            left_text = left.passage.casefold()
            left_pos = any(word in left_text for word in _POSITIVE_CUES)
            left_neg = any(word in left_text for word in _NEGATIVE_CUES)
            if not (left_pos or left_neg):
                continue
            for right in items[index + 1:]:
                right_text = right.passage.casefold()
                right_pos = any(word in right_text for word in _POSITIVE_CUES)
                right_neg = any(word in right_text for word in _NEGATIVE_CUES)
                if (left_pos and right_neg) or (left_neg and right_pos):
                    conflicts.append({
                        "criterion_key": criterion,
                        "left_locator": left.source_locator,
                        "right_locator": right.source_locator,
                        "status": "POTENTIAL_CONFLICT_REQUIRES_REVIEW",
                        "reason": "Opposing directional language detected by heuristic; context and dates must be reviewed.",
                    })
    return tuple(conflicts)
