from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.portfolio_benchmarks import BenchmarkCreate, BenchmarkObservationCreate
from app.services.portfolio.performance.benchmark import calculate_relative_performance


def test_benchmark_requires_total_return_index_and_provenance():
    item = BenchmarkCreate.model_validate({
        "code": "SP500TR", "name": "S&P 500 Total Return", "currency": "USD",
        "provider": "Manual import", "methodology": "Total return index, dividends reinvested",
    })
    assert item.benchmark_type == "TOTAL_RETURN_INDEX"
    with pytest.raises(ValidationError):
        BenchmarkCreate.model_validate({
            "code": "SP500", "name": "S&P 500", "currency": "USD",
            "benchmark_type": "PRICE_INDEX", "provider": "Manual", "methodology": "Price only",
        })


def test_observation_requires_positive_finite_level_and_matching_currency_shape():
    payload = {
        "observation_date": "2026-01-31", "index_level": "125.5", "currency": "EUR",
        "source": "Manual CSV", "methodology": "Vendor total-return close",
    }
    assert BenchmarkObservationCreate.model_validate(payload).index_level == Decimal("125.5")
    with pytest.raises(ValidationError):
        BenchmarkObservationCreate.model_validate({**payload, "index_level": "NaN"})
    with pytest.raises(ValidationError):
        BenchmarkObservationCreate.model_validate({**payload, "currency": "EURO"})


def test_relative_performance_calculates_excess_return_in_percentage_points():
    result = calculate_relative_performance(
        portfolio_twr="0.12", benchmark_start_level="100", benchmark_end_level="110",
        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
        portfolio_currency="EUR", benchmark_currency="EUR",
    )
    assert Decimal(result["benchmark_total_return"]) == Decimal("0.1")
    assert Decimal(result["relative_return"]) == Decimal("0.02")
    assert Decimal(result["relative_return_percentage_points"]) == Decimal("2.00")


def test_relative_performance_rejects_currency_mismatch_and_invalid_levels():
    args = {
        "portfolio_twr": "0.1",
        "benchmark_start_level": "100",
        "benchmark_end_level": "110",
        "start_date": date(2026, 1, 1),
        "end_date": date(2026, 2, 1),
        "portfolio_currency": "EUR",
        "benchmark_currency": "USD",
    }
    with pytest.raises(ValueError, match="currencies must match"):
        calculate_relative_performance(**args)
    with pytest.raises(ValueError, match="positive"):
        calculate_relative_performance(**{**args, "benchmark_currency": "EUR", "benchmark_end_level": "0"})
