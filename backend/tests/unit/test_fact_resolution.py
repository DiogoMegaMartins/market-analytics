from datetime import date

import pytest

from app.domain.fact_resolution import ResolutionPolicy, eligible_by_policy


def test_latest_restate_accepts_filed_fact() -> None:
    assert eligible_by_policy(filed_at=None, policy=ResolutionPolicy.LATEST_RESTATED, cutoff=None)


def test_as_known_at_excludes_unknown_or_future_filing() -> None:
    cutoff = date(2024, 12, 31)
    assert not eligible_by_policy(filed_at=None, policy=ResolutionPolicy.AS_KNOWN_AT, cutoff=cutoff)
    assert not eligible_by_policy(filed_at=date(2025, 1, 2), policy=ResolutionPolicy.AS_KNOWN_AT, cutoff=cutoff)
    assert eligible_by_policy(filed_at=date(2024, 12, 30), policy=ResolutionPolicy.AS_KNOWN_AT, cutoff=cutoff)


def test_as_known_at_requires_cutoff() -> None:
    with pytest.raises(ValueError):
        eligible_by_policy(filed_at=date(2024, 1, 1), policy=ResolutionPolicy.AS_KNOWN_AT, cutoff=None)
