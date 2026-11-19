from __future__ import annotations

import asyncio
import email.utils
import json
from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any, ClassVar

import httpx

from app.core.config import get_settings
from app.core.observability import metrics


class SECProviderError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class SECForbiddenError(SECProviderError):
    """SEC denied the request; usually indicates an invalid User-Agent or access policy issue."""


class SECRateLimitError(SECProviderError):
    """SEC rate limit remained active after the configured retries."""


class SECClient:
    """SEC data.sec.gov client with bounded retries and conservative per-process throttling.

    A process-local limiter is not a distributed quota manager. Multi-worker deployments
    must add a shared limiter before increasing SEC request concurrency.
    """

    TICKER_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
    SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    RETRYABLE_STATUS_CODES: ClassVar[set[int]] = {429, 500, 502, 503, 504}

    def __init__(
        self, *, timeout: float = 15.0, min_interval: float = 0.20,
        max_attempts: int | None = None, base_backoff: float | None = None,
        max_backoff: float | None = None,
    ) -> None:
        settings = get_settings()
        self.timeout = timeout
        self.min_interval = min_interval
        self.max_attempts = max_attempts or settings.sec_max_attempts
        self.base_backoff = base_backoff if base_backoff is not None else settings.sec_retry_base_seconds
        self.max_backoff = max_backoff if max_backoff is not None else settings.sec_retry_max_seconds
        self._lock = asyncio.Lock()
        self._last_request = 0.0

    @staticmethod
    def normalize_cik(cik: str) -> str:
        value = str(cik).strip()
        if not value.isdigit() or len(value) > 10:
            raise ValueError("CIK must contain at most 10 digits")
        return value.zfill(10)

    @staticmethod
    def _retry_after_seconds(value: str | None) -> float | None:
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                parsed = email.utils.parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=UTC)
                return max(0.0, (parsed - datetime.now(UTC)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return None

    async def _throttle(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            wait = self.min_interval - (loop.time() - self._last_request)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request = loop.time()

    async def _get_response(self, url: str) -> httpx.Response:
        settings = get_settings()
        headers = {
            "User-Agent": settings.sec_user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Host": "www.sec.gov" if "www.sec.gov" in url else "data.sec.gov",
        }
        attempts = max(1, self.max_attempts)
        last_error: Exception | None = None

        for attempt in range(attempts):
            await self._throttle()
            try:
                metrics.increment("market_analytics_provider_attempts_total", {"provider": "sec"})
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.get(url, headers=headers)
            except httpx.TimeoutException as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    break
                metrics.increment("market_analytics_provider_retries_total", {"provider": "sec"})
                await asyncio.sleep(min(self.base_backoff * (2 ** attempt), self.max_backoff))
                continue
            except httpx.TransportError as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    break
                metrics.increment("market_analytics_provider_retries_total", {"provider": "sec"})
                await asyncio.sleep(min(self.base_backoff * (2 ** attempt), self.max_backoff))
                continue
            except httpx.HTTPError as exc:
                metrics.increment(
                    "market_analytics_provider_failures_total",
                    {"provider": "sec", "reason": "transport_error"},
                )
                raise SECProviderError(
                    f"SEC transport error: {type(exc).__name__}", retryable=False
                ) from exc

            if response.status_code == 403:
                metrics.increment("market_analytics_provider_failures_total", {"provider": "sec", "reason": "forbidden"})
                raise SECForbiddenError(
                    "SEC returned HTTP 403; verify the User-Agent, contact details and access policy",
                    status_code=403,
                )
            if response.status_code == 429:
                last_error = SECRateLimitError(
                    "SEC rate limit remained active", status_code=429, retryable=True
                )
                if attempt + 1 >= attempts:
                    break
                metrics.increment("market_analytics_provider_retries_total", {"provider": "sec"})
                retry_after = self._retry_after_seconds(response.headers.get("Retry-After"))
                delay = retry_after if retry_after is not None else min(
                    self.base_backoff * (2 ** attempt), self.max_backoff
                )
                await asyncio.sleep(delay)
                continue
            if response.status_code in self.RETRYABLE_STATUS_CODES:
                last_error = SECProviderError(
                    f"SEC temporary HTTP error {response.status_code}",
                    status_code=response.status_code, retryable=True,
                )
                if attempt + 1 >= attempts:
                    break
                metrics.increment("market_analytics_provider_retries_total", {"provider": "sec"})
                retry_after = self._retry_after_seconds(response.headers.get("Retry-After"))
                delay = retry_after if retry_after is not None else min(
                    self.base_backoff * (2 ** attempt), self.max_backoff
                )
                await asyncio.sleep(delay)
                continue
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                metrics.increment(
                    "market_analytics_provider_failures_total",
                    {"provider": "sec", "reason": "http_error"},
                )
                raise SECProviderError(
                    f"SEC request failed with HTTP {response.status_code}",
                    status_code=response.status_code,
                ) from exc
            metrics.increment("market_analytics_provider_success_total", {"provider": "sec"})
            return response

        metrics.increment("market_analytics_provider_failures_total", {"provider": "sec", "reason": "retries_exhausted"})
        if isinstance(last_error, SECRateLimitError):
            raise last_error
        raise SECProviderError(
            f"SEC request failed after {attempts} attempt(s): "
            f"{type(last_error).__name__ if last_error else 'unknown error'}",
            retryable=True,
        ) from last_error

    async def _get_json(self, url: str) -> dict[str, Any]:
        response = await self._get_response(url)
        try:
            payload = response.json()
        except ValueError as exc:
            raise SECProviderError("SEC returned invalid JSON") from exc
        if not isinstance(payload, dict):
            raise SECProviderError("SEC returned an unexpected JSON structure")
        return payload

    async def ticker_exchange_data(self) -> dict[str, Any]:
        return await self._get_json(self.TICKER_EXCHANGE_URL)

    async def submissions(self, cik: str) -> dict[str, Any]:
        padded = self.normalize_cik(cik)
        return await self._get_json(self.SUBMISSIONS_URL.format(cik=padded))

    async def submissions_file(self, filename: str) -> dict[str, Any]:
        """Fetch an SEC submissions shard referenced by the submissions index."""
        if not filename or "/" in filename or "\\" in filename or not filename.endswith(".json"):
            raise ValueError("Invalid SEC submissions filename")
        return await self._get_json(f"https://data.sec.gov/submissions/{filename}")

    async def company_facts(self, cik: str) -> tuple[dict[str, Any], str, str]:
        """Return parsed Company Facts, exact response text and SHA-256 of response bytes."""
        padded = self.normalize_cik(cik)
        url = self.COMPANY_FACTS_URL.format(cik=padded)
        response = await self._get_response(url)
        raw_bytes = response.content
        try:
            raw_text = raw_bytes.decode(response.encoding or "utf-8")
            payload = json.loads(raw_text, parse_float=Decimal, parse_int=int)
        except (UnicodeDecodeError, ValueError) as exc:
            raise SECProviderError("SEC Company Facts response was not valid JSON") from exc
        if not isinstance(payload, dict):
            raise SECProviderError("SEC Company Facts response has an unexpected structure")
        return payload, raw_text, sha256(raw_bytes).hexdigest()
