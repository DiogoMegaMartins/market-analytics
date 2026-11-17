from datetime import date

import pytest

from app.domain.fact_resolution import ResolutionPolicy, eligible_by_policy


def test_as_known_at_excludes_later_filing():
    assert eligible_by_policy(filed_at=date(2024, 3, 1), policy=ResolutionPolicy.AS_KNOWN_AT,
                              cutoff=date(2024, 3, 2))
    assert not eligible_by_policy(filed_at=date(2024, 3, 3), policy=ResolutionPolicy.AS_KNOWN_AT,
                                  cutoff=date(2024, 3, 2))


def test_as_known_at_requires_cutoff():
    with pytest.raises(ValueError):
        eligible_by_policy(filed_at=None, policy=ResolutionPolicy.AS_KNOWN_AT, cutoff=None)
