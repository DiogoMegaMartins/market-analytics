from dataclasses import dataclass
from typing import Any

from app.providers.sec.client import SECClient


@dataclass(frozen=True)
class SECTickerCandidate:
    cik: str
    name: str
    ticker: str
    exchange: str | None


class SECTickerResolver:
    def __init__(self, client: SECClient | None = None) -> None:
        self.client = client or SECClient()

    async def resolve_ticker(self, ticker: str) -> list[SECTickerCandidate]:
        normalized = ticker.strip().upper()
        if not normalized:
            raise ValueError("Ticker cannot be empty")
        payload = await self.client.ticker_exchange_data()
        rows = payload.get("data", [])
        candidates: list[SECTickerCandidate] = []
        for row in rows:
            if len(row) < 4 or str(row[2]).upper() != normalized:
                continue
            candidates.append(
                SECTickerCandidate(
                    cik=str(row[0]).zfill(10),
                    name=str(row[1]),
                    ticker=str(row[2]).upper(),
                    exchange=str(row[3]) if row[3] else None,
                )
            )
        return candidates

    async def verify_cik(self, cik: str) -> dict[str, Any]:
        return await self.client.submissions(cik)
