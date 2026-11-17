from datetime import date

import pytest

from app.services.research.what_changed import build_what_changed


def _brief(documents=(), passages=(), **counts):
    return {
        "source_documents": list(documents),
        "evidence_candidates": list(passages),
        "summary": counts,
    }


def _assessment(score, dimension_score):
    return {
        "id": f"assessment-{score}",
        "created_at": "2025-01-01T00:00:00+00:00",
        "engine_version": "bq-v1",
        "rubric_version": "bq-v1",
        "status": "COMPLETE",
        "overall_score": score,
        "classification": "STRONG",
        "results": {"dimensions": [{"dimension": "Revenue Quality", "score": dimension_score}]},
    }


def test_what_changed_detects_new_filings_evidence_and_dimension_delta():
    old_doc = {"document_id": "doc-1", "accession_number": "old"}
    new_doc = {"document_id": "doc-2", "accession_number": "new"}
    old_passage = {"criterion_key": "risk", "passage_type": "RISK", "source": {"document_id": "doc-1", "section_id": "s1"}}
    new_passage = {"criterion_key": "growth", "passage_type": "MANAGEMENT", "source": {"document_id": "doc-2", "section_id": "s2"}}

    result = build_what_changed(
        company_id="company-1", company_name="Example Corp",
        from_date=date(2024, 12, 31), to_date=date(2025, 12, 31),
        before_brief=_brief([old_doc], [old_passage], risk_disclosure_count=1),
        after_brief=_brief([old_doc, new_doc], [old_passage, new_passage], risk_disclosure_count=1),
        before_assessment=_assessment("60", "55"),
        after_assessment=_assessment("70", "65"),
    )

    assert result["filings"]["added"] == [new_doc]
    assert result["evidence"]["new_candidates"] == [new_passage]
    assert result["business_quality"]["dimension_changes"][0]["delta"] == "10"
    assert result["interpretation"]["causality_established"] is False
    assert result["interpretation"]["fair_value_modified"] is False
    assert result["analyst_review_required"] is True


def test_what_changed_marks_passages_no_longer_retrieved_without_calling_them_removed_risks():
    passage = {"criterion_key": "risk", "passage_type": "RISK", "source": {"document_id": "doc-1", "section_id": "s1"}}
    result = build_what_changed(
        company_id="c", company_name="C", from_date=date(2024, 1, 1), to_date=date(2025, 1, 1),
        before_brief=_brief(passages=[passage]), after_brief=_brief(),
    )
    assert result["evidence"]["no_longer_retrieved"] == [passage]
    assert any("not proof" in item for item in result["interpretation"]["limitations"])


def test_what_changed_handles_missing_assessments_and_no_change():
    result = build_what_changed(
        company_id="c", company_name="C", from_date=date(2024, 1, 1), to_date=date(2025, 1, 1),
        before_brief=_brief(), after_brief=_brief(),
    )
    assert result["business_quality"]["previous_assessment"] is None
    assert result["business_quality"]["current_assessment"] is None
    assert result["changes"] == [{"type": "NO_DETECTED_CHANGE", "count": 0, "severity": "INFO"}]


def test_what_changed_only_compares_finite_dimension_scores():
    assessment = {
        "results": {"dimensions": [
            {"dimension": "Good", "score": "50"},
            {"dimension": "Bad", "score": "NaN"},
        ]}
    }
    result = build_what_changed(
        company_id="c", company_name="C", from_date=date(2024, 1, 1), to_date=date(2025, 1, 1),
        before_brief=_brief(), after_brief=_brief(),
        before_assessment=assessment, after_assessment=None,
    )
    assert result["business_quality"]["previous_assessment"]["dimensions"] == {"Good": "50"}


def test_what_changed_requires_ordered_dates():
    with pytest.raises(ValueError, match="from_date"):
        build_what_changed(
            company_id="c", company_name="C", from_date=date(2025, 1, 1), to_date=date(2025, 1, 1),
            before_brief=_brief(), after_brief=_brief(),
        )


def test_what_changed_route_is_company_scoped_and_registered():
    from app.api.v1.endpoints.business_quality import router

    route = next((item for item in router.routes if getattr(item, "path", None) ==
                  "/research/companies/{company_id}/what-changed"), None)
    assert route is not None
    assert "GET" in route.methods
    assert any(getattr(dependency.dependency, "__name__", "") == "require_company_access"
               for dependency in router.dependencies)
