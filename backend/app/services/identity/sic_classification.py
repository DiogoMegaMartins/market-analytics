"""Conservative issuer-sector classification from SEC Standard Industrial Classification codes."""

from enum import StrEnum


class SICSector(StrEnum):
    BANKING = "BANKING"
    INSURANCE = "INSURANCE"
    REIT = "REIT"
    OTHER = "OTHER"


def classify_sic(sic_code: str | int | None) -> SICSector | None:
    """Classify only the sectors that require a specialist valuation method.

    Returns None for absent or malformed SIC codes. The classification is a
    narrow suitability guard, not a complete industry taxonomy.
    """
    if sic_code is None:
        return None
    code = str(sic_code).strip()
    if len(code) != 4 or not code.isascii() or not code.isdigit():
        return None

    numeric = int(code)
    if 6000 <= numeric <= 6199:
        return SICSector.BANKING
    if 6311 <= numeric <= 6399:
        return SICSector.INSURANCE
    if numeric == 6798:
        return SICSector.REIT
    return SICSector.OTHER
