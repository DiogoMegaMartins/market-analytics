from decimal import Decimal

from app.services.metrics.calculator import (
    MetricStatus,
    calculate_annual_metrics,
    calculate_cagr,
    calculate_growth,
)


def test_annual_metrics_calculate_fcf_and_margins():
    results = calculate_annual_metrics({
        "FIN.REVENUE": Decimal(1000),
        "FIN.OPERATING_INCOME": Decimal(200),
        "FIN.NET_INCOME": Decimal(150),
        "FIN.OCF": Decimal(180),
        "FIN.CAPEX": Decimal(40),
    })
    values = {result.metric_id: result for result in results}
    assert values["FIN.FCF"].value == Decimal(140)
    assert values["FIN.OPERATING_MARGIN"].value == Decimal("0.2")
    assert values["FIN.FCF_MARGIN"].value == Decimal("0.14")


def test_negative_capex_is_not_silently_absed():
    values = {r.metric_id: r for r in calculate_annual_metrics({
        "FIN.REVENUE": Decimal(100), "FIN.OCF": Decimal(50),
        "FIN.CAPEX": Decimal(-10),
    })}
    assert values["FIN.FCF"].status == MetricStatus.INVALID_INPUT
    assert values["FIN.FCF"].value is None


def test_missing_and_zero_denominators_are_explicit():
    values = {r.metric_id: r for r in calculate_annual_metrics({
        "FIN.REVENUE": Decimal(0), "FIN.OPERATING_INCOME": Decimal(5),
    })}
    assert values["FIN.OPERATING_MARGIN"].status == MetricStatus.INVALID_INPUT
    assert values["FIN.FCF"].status == MetricStatus.UNAVAILABLE


def test_growth_requires_positive_prior_revenue():
    assert calculate_growth(Decimal(120), Decimal(100)).value == Decimal("0.2")
    assert calculate_growth(Decimal(120), Decimal(0)).status == MetricStatus.INVALID_INPUT


def test_cagr_uses_elapsed_years():
    result = calculate_cagr(Decimal(100), Decimal(121), 2)
    assert abs(result.value - Decimal("0.1")) < Decimal("1e-20")


def test_cagr_rejects_invalid_endpoints():
    assert calculate_cagr(Decimal(0), Decimal(100), 5).status == MetricStatus.INVALID_INPUT
