"""Deterministic, citation-first research brief assembly.

This is a retrieval and organization layer, not an LLM-generated investment opinion.
It preserves source dates and locators and never treats extracted passages as verified facts.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from app.services.business_quality.evidence_extraction import (
    EvidencePassage,
    detect_potential_conflicts,
    extract_evidence_candidates,
)

RESEARCH_BRIEF_VERSION = "research-brief-v1.0.0"


@dataclass(frozen=True)
class ResearchSection:
    section_id: str
    section_key: str
    heading: str
    sequence_number: int
    text_content: str


@dataclass(frozen=True)
class ResearchDocument:
    document_id: str
    accession_number: str
    form_type: str
    filed_at: datetime
    published_at: datetime | None
    source_url: str
    document_hash: str
    sections: tuple[ResearchSection, ...]


def build_research_brief(
    *, company_id: str, company_name: str, documents: Iterable[ResearchDocument],
    as_of: date | None = None, max_passages: int = 200,
) -> dict:
    """Build a reproducible filing-based brief with source-linked candidate passages."""
    if not 1 <= max_passages <= 1000:
        raise ValueError("max_passages must be between 1 and 1000")

    eligible = [doc for doc in documents if as_of is None or doc.filed_at.date() <= as_of]
    eligible.sort(key=lambda doc: (doc.filed_at, doc.accession_number), reverse=True)
    passages: list[dict] = []
    typed: list[EvidencePassage] = []
    risk_disclosures: list[dict] = []
    management_assertions: list[dict] = []
    quantitative_claims: list[dict] = []

    for doc in eligible:
        for section in sorted(doc.sections, key=lambda item: item.sequence_number):
            extracted = extract_evidence_candidates(
                section.text_content, section_key=section.section_key, max_candidates=200,
            )
            for item in extracted:
                if len(passages) >= max_passages:
                    break
                locator = {
                    "document_id": doc.document_id,
                    "section_id": section.section_id,
                    "section_heading": section.heading,
                    "section_key": section.section_key,
                    "source_locator": item.source_locator,
                    "accession_number": doc.accession_number,
                    "form_type": doc.form_type,
                    "filed_at": doc.filed_at.isoformat(),
                    "published_at": doc.published_at.isoformat() if doc.published_at else None,
                    "source_url": doc.source_url,
                    "document_hash": doc.document_hash,
                }
                entry = {
                    "criterion_key": item.criterion_key,
                    "dimension": item.dimension,
                    "passage": item.passage,
                    "passage_type": item.passage_type,
                    "matched_cues": list(item.matched_cues),
                    "status": "UNVERIFIED_CANDIDATE",
                    "source": locator,
                    "interpretation": "Retrieval match only; analyst verification and contextual reading are required.",
                }
                passages.append(entry)
                typed.append(EvidencePassage(
                    criterion_key=item.criterion_key, dimension=item.dimension,
                    passage=item.passage, source_locator=(
                        f"{doc.accession_number}:{section.section_key}:{item.source_locator}"
                    ), passage_type=item.passage_type, matched_cues=item.matched_cues,
                    rationale=item.rationale, extraction_version=item.extraction_version,
                ))
                if item.passage_type == "RISK_DISCLOSURE":
                    risk_disclosures.append(entry)
                elif item.passage_type == "MANAGEMENT_ASSERTION":
                    management_assertions.append(entry)
                elif item.passage_type == "QUANTITATIVE_CLAIM":
                    quantitative_claims.append(entry)
            if len(passages) >= max_passages:
                break
        if len(passages) >= max_passages:
            break

    conflicts = list(detect_potential_conflicts(typed))
    return {
        "brief_version": RESEARCH_BRIEF_VERSION,
        "company_id": company_id,
        "company_name": company_name,
        "as_of_filing_date": as_of.isoformat() if as_of else None,
        "source_document_count": len(eligible),
        "source_documents": [
            {"document_id": doc.document_id, "accession_number": doc.accession_number,
             "form_type": doc.form_type, "filed_at": doc.filed_at.isoformat(),
             "published_at": doc.published_at.isoformat() if doc.published_at else None,
             "source_url": doc.source_url, "document_hash": doc.document_hash,
             "section_count": len(doc.sections)}
            for doc in eligible
        ],
        "summary": {
            "candidate_passage_count": len(passages),
            "risk_disclosure_count": len(risk_disclosures),
            "management_assertion_count": len(management_assertions),
            "quantitative_claim_count": len(quantitative_claims),
            "potential_conflict_count": len(conflicts),
        },
        "risk_disclosures": risk_disclosures,
        "management_assertions": management_assertions,
        "quantitative_claims": quantitative_claims,
        "evidence_candidates": passages,
        "potential_conflicts": conflicts,
        "methodology": {
            "retrieval": "Deterministic keyword-based passage extraction",
            "scoring_performed": False,
            "claims_verified": False,
            "investment_recommendation_generated": False,
            "date_policy": "Filtered by SEC filing date; filing date is not proof of exact public availability time.",
            "limitations": [
                "Only previously ingested SEC filing sections are included; no live filing download occurs here.",
                "Keyword matches can miss relevant passages and can produce false positives.",
                "Potential conflicts are heuristic flags, not adjudicated contradictions.",
                "Management statements are attributed assertions, not independently verified facts.",
                "Quantitative passages require reconciliation against reported financial facts and units.",
            ],
        },
        "analyst_review_required": True,
    }
