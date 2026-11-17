from datetime import UTC, date, datetime

import pytest

from app.services.research.brief import (
    RESEARCH_BRIEF_VERSION,
    ResearchDocument,
    ResearchSection,
    build_research_brief,
)


def _document(*, accession: str, filed: datetime, text: str) -> ResearchDocument:
    return ResearchDocument(
        document_id=f"doc-{accession}", accession_number=accession,
        form_type="10-K", filed_at=filed, published_at=None,
        source_url=f"https://www.sec.gov/Archives/edgar/data/1/{accession}/",
        document_hash="a" * 64,
        sections=(ResearchSection(
            section_id=f"section-{accession}", section_key="MD&A",
            heading="Management discussion", sequence_number=1, text_content=text,
        ),),
    )


def test_research_brief_preserves_source_citations_and_separates_claim_types():
    doc = _document(
        accession="0000000001-25-000001",
        filed=datetime(2025, 2, 1, tzinfo=UTC),
        text=(
            "We expect organic growth to improve next year. "
            "Customer demand risk could adversely affect operating results. "
            "Organic growth increased by 12% during the year."
        ),
    )

    result = build_research_brief(company_id="company-1", company_name="Example Corp", documents=[doc])

    assert result["brief_version"] == RESEARCH_BRIEF_VERSION
    assert result["analyst_review_required"] is True
    assert result["methodology"]["scoring_performed"] is False
    assert result["methodology"]["investment_recommendation_generated"] is False
    assert result["summary"]["candidate_passage_count"] >= 2
    assert result["summary"]["risk_disclosure_count"] >= 1
    assert result["summary"]["management_assertion_count"] >= 1
    candidate = result["evidence_candidates"][0]
    assert candidate["status"] == "UNVERIFIED_CANDIDATE"
    assert candidate["source"]["accession_number"] == doc.accession_number
    assert candidate["source"]["source_url"].startswith("https://www.sec.gov/")


def test_research_brief_as_of_uses_filing_date_cutoff():
    older = _document(accession="old", filed=datetime(2024, 2, 1, tzinfo=UTC),
                      text="Our business model supports recurring revenue growth.")
    newer = _document(accession="new", filed=datetime(2025, 2, 1, tzinfo=UTC),
                      text="Our business model supports recurring revenue growth.")

    result = build_research_brief(
        company_id="company-1", company_name="Example Corp", documents=[older, newer],
        as_of=date(2024, 12, 31),
    )

    assert result["source_document_count"] == 1
    assert result["source_documents"][0]["accession_number"] == "old"
    assert result["as_of_filing_date"] == "2024-12-31"


def test_research_brief_rejects_unbounded_passage_limit():
    with pytest.raises(ValueError, match="max_passages"):
        build_research_brief(company_id="c", company_name="C", documents=[], max_passages=1001)


def test_research_brief_route_is_registered_under_company_scoped_api():
    from app.api.v1.endpoints.business_quality import router

    route = next((item for item in router.routes if getattr(item, "path", None) ==
                  "/research/companies/{company_id}/brief"), None)
    assert route is not None
    assert "GET" in route.methods
    assert any(getattr(dependency.dependency, "__name__", "") == "require_company_access"
               for dependency in router.dependencies)
