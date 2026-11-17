from datetime import date
from enum import StrEnum


class ResolutionPolicy(StrEnum):
    LATEST_RESTATED = "LATEST_RESTATED"
    AS_KNOWN_AT = "AS_KNOWN_AT"


def eligible_by_policy(*, filed_at: date | None, policy: ResolutionPolicy, cutoff: date | None) -> bool:
    if policy == ResolutionPolicy.LATEST_RESTATED:
        return True
    if cutoff is None:
        raise ValueError("AS_KNOWN_AT requires an as_known_at cutoff date")
    # Unknown filing dates cannot be asserted to have been available by the cutoff.
    return filed_at is not None and filed_at <= cutoff
