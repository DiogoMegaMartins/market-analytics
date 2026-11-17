from datetime import date
from decimal import Decimal

import pytest

from app.services.business_quality.historical_validation import (
    HistoricalAssessment,
    validate_historical_assessments,
)


def row(company, period, score, *, version="v1", approved=True, completeness="100", ident=None):
    return HistoricalAssessment(company, ident or f"{company}-{period}", date.fromisoformat(period),
                                Decimal(str(score)) if score is not None else None,
                                Decimal(completeness), "HIGH", version, approved)


def test_historical_report_tracks_company_change_and_rank_consistency():
    rows = [row("A", "2024-12-31", 90), row("B", "2024-12-31", 70), row("C", "2024-12-31", 50),
            row("A", "2025-12-31", 80), row("B", "2025-12-31", 75), row("C", "2025-12-31", 55)]
    report = validate_historical_assessments(rows)
    a = next(x for x in report.company_histories if x.company_key == "A")
    assert a.absolute_change == Decimal(-10)
    assert report.rank_consistency[0].spearman_rho == Decimal("1.0000")


def test_unapproved_and_incomplete_are_excluded_not_scored_zero():
    rows = [row("A", "2025-12-31", 80), row("B", "2025-12-31", 90, approved=False),
            row("C", "2025-12-31", 70, completeness="40")]
    result = validate_historical_assessments(rows)
    period = result.period_coverage[0]
    assert period.eligible_companies == 1
    assert period.excluded_unapproved == 1
    assert period.excluded_incomplete == 1


def test_duplicate_company_period_is_rejected():
    with pytest.raises(ValueError, match="Duplicate company"):
        validate_historical_assessments([row("A", "2025-12-31", 80), row("A", "2025-12-31", 70, ident="other")])


def test_methodology_mismatch_prevents_rank_correlation():
    rows = [row("A", "2024-12-31", 90), row("B", "2024-12-31", 70), row("C", "2024-12-31", 50),
            row("A", "2025-12-31", 80, version="v2"), row("B", "2025-12-31", 75, version="v2"), row("C", "2025-12-31", 55, version="v2")]
    report = validate_historical_assessments(rows)
    assert report.rank_consistency[0].status == "METHODOLOGY_MISMATCH"
    assert report.rank_consistency[0].spearman_rho is None
