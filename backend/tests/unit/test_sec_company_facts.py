from app.providers.sec.client import SECClient
from app.services.financial_data.sec_company_facts import SEC_TAG_MAP, _currency_for_unit


def test_cik_normalization_and_validation() -> None:
    assert SECClient.normalize_cik("789019") == "0000789019"
    try:
        SECClient.normalize_cik("abc")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid CIK should fail")


def test_mapping_uses_ordered_revenue_alternatives() -> None:
    assert SEC_TAG_MAP["FIN.REVENUE"][0] == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert len(SEC_TAG_MAP["FIN.REVENUE"]) > 1


def test_currency_detection_does_not_misclassify_shares() -> None:
    assert _currency_for_unit("USD") == "USD"
    assert _currency_for_unit("shares") is None
    assert _currency_for_unit("USD/shares") is None
