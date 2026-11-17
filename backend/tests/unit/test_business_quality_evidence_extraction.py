from app.services.business_quality.evidence_extraction import (
    EXTRACTION_VERSION,
    criterion_catalog,
    detect_potential_conflicts,
    extract_evidence_candidates,
)


def test_catalog_is_derived_from_rubric_and_has_unique_keys():
    catalog = criterion_catalog()
    keys = [item.criterion_key for item in catalog]
    assert len(catalog) == 25
    assert len(keys) == len(set(keys))
    assert "COMPETITIVE_MOAT.pricing_power" in keys
    assert "MANAGEMENT_ALLOCATION.governance" in keys
    assert all(item.dimension and item.label for item in catalog)


def test_extracts_candidate_passages_without_claiming_verification():
    text = (
        "Our subscription revenue is recurring and customers typically renew annually. "
        "We believe our pricing power allows us to increase prices over time. "
        "The company faces risk from supplier concentration and dependency on one vendor. "
    )
    results = extract_evidence_candidates(text, section_key="BUSINESS")
    assert results
    assert {item.criterion_key for item in results} >= {
        "REVENUE_QUALITY.recurrence", "COMPETITIVE_MOAT.pricing_power", "BUSINESS_MODEL.dependencies"
    }
    assert all(item.extraction_version == EXTRACTION_VERSION for item in results)
    assert all("not a verified fact" in item.rationale for item in results)
    assert any(item.passage_type == "MANAGEMENT_ASSERTION" for item in results)
    assert any(item.passage_type == "RISK_DISCLOSURE" for item in results)


def test_quantitative_claim_is_labelled_as_candidate_not_fact():
    text = "Operating cash flow increased to $12.4 billion during the fiscal year."
    results = extract_evidence_candidates(text, section_key="MD&A")
    assert results
    assert all(item.passage_type == "QUANTITATIVE_CLAIM" for item in results)


def test_potential_conflicts_are_flagged_but_not_resolved():
    text = (
        "Our pricing power allowed prices to increase during the year. "
        "Our pricing power weakened and price increases were lower in several important markets."
    )
    results = extract_evidence_candidates(text, section_key="MD&A")
    conflicts = detect_potential_conflicts(results)
    assert conflicts
    assert all(item["status"] == "POTENTIAL_CONFLICT_REQUIRES_REVIEW" for item in conflicts)


def test_empty_text_and_limits_are_handled():
    assert extract_evidence_candidates("  ", section_key="RISK_FACTORS") == ()
    try:
        extract_evidence_candidates("text", section_key="BUSINESS", max_candidates=0)
    except ValueError as exc:
        assert "max_candidates" in str(exc)
    else:
        raise AssertionError("invalid candidate limit should fail")
