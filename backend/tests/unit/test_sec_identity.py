import pytest

from app.services.identity.sec_identity import SECTickerResolver


class FakeSECClient:
    async def ticker_exchange_data(self):
        return {"data": [
            [789019, "MICROSOFT CORP", "MSFT", "Nasdaq"],
            [320193, "Apple Inc.", "AAPL", "Nasdaq"],
            [123456, "Other Company", "MSFT", "NYSE"],
        ]}


@pytest.mark.asyncio
async def test_resolver_returns_all_candidates_and_pads_cik():
    candidates = await SECTickerResolver(FakeSECClient()).resolve_ticker(" msft ")
    assert len(candidates) == 2
    assert candidates[0].cik == "0000789019"
    assert candidates[1].exchange == "NYSE"


@pytest.mark.asyncio
async def test_resolver_returns_empty_for_unknown_ticker():
    candidates = await SECTickerResolver(FakeSECClient()).resolve_ticker("UNKNOWN")
    assert candidates == []


@pytest.mark.asyncio
async def test_resolver_rejects_empty_ticker():
    with pytest.raises(ValueError):
        await SECTickerResolver(FakeSECClient()).resolve_ticker("  ")
