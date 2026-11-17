from datetime import UTC, datetime, timedelta

import pytest

from app.services.business_quality.point_in_time import (
    EvidenceRecord,
    build_point_in_time_manifest,
    evaluate_point_in_time_evidence,
)

T0 = datetime(2024, 1, 1, tzinfo=UTC)


def record(eid="e1", published=T0, available=T0, captured=T0):
    return EvidenceRecord(eid, "MOAT.PRICING_POWER", "Annual report", "https://example.test/report",
                          published, available, captured, "sha256:abc")


def test_evidence_available_before_cutoff_is_eligible():
    result = evaluate_point_in_time_evidence([record()], as_of=T0 + timedelta(days=1))
    assert result[0].eligible and result[0].reason == "AVAILABLE_AS_OF_CUTOFF"


def test_future_publication_is_excluded_even_if_captured_later():
    future = T0 + timedelta(days=10)
    result = evaluate_point_in_time_evidence([record(published=future, available=future, captured=future)], as_of=T0)
    assert not result[0].eligible
    assert result[0].reason == "PUBLISHED_AFTER_CUTOFF"


def test_missing_availability_is_unverifiable_not_eligible():
    result = evaluate_point_in_time_evidence([record(available=None)], as_of=T0)
    assert not result[0].eligible
    assert result[0].reason == "UNVERIFIABLE_AVAILABILITY_DATE"


def test_naive_cutoff_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate_point_in_time_evidence([], as_of=datetime(2024, 1, 1))


def test_manifest_preserves_hash_and_exclusions():
    manifest = build_point_in_time_manifest([record(), record("e2", published=None, available=None)], as_of=T0)
    assert manifest["policy_version"] == "PIT_EVIDENCE_1.0.0"
    assert manifest["eligible_evidence_ids"] == ["e1"]
    assert manifest["excluded"][0]["reason"] == "UNVERIFIABLE_AVAILABILITY_DATE"
    assert manifest["evidence"][0]["content_hash"] == "sha256:abc"


def test_duplicate_ids_rejected():
    with pytest.raises(ValueError, match="unique"):
        evaluate_point_in_time_evidence([record(), record()], as_of=T0)
