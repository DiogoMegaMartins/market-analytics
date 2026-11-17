import json
from typing import ClassVar

import httpx
import pytest

from app.models.financial_data import SECProviderCache
from app.providers.sec import client as sec_module
from app.providers.sec.client import SECClient, SECForbiddenError, SECRateLimitError


class FakeResponse:
    def __init__(self, status_code=200, *, headers=None, payload=None, content=None):
        self.status_code = status_code
        self.headers = headers or {}
        self._payload = payload or {"facts": {"us-gaap": {}}}
        self.content = content if content is not None else json.dumps(self._payload).encode()
        self.encoding = "utf-8"

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://data.sec.gov/test")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)


class FakeAsyncClient:
    responses: ClassVar[list] = []
    calls: ClassVar[int] = 0

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers):
        type(self).calls += 1
        item = type(self).responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


@pytest.mark.asyncio
async def test_sec_client_retries_429_then_succeeds(monkeypatch):
    FakeAsyncClient.responses = [
        FakeResponse(429, headers={"Retry-After": "0"}),
        FakeResponse(200, payload={"facts": {"us-gaap": {}}}),
    ]
    FakeAsyncClient.calls = 0
    monkeypatch.setattr(sec_module.httpx, "AsyncClient", FakeAsyncClient)
    sleeps = []
    async def fake_sleep(seconds):
        sleeps.append(seconds)
    monkeypatch.setattr(sec_module.asyncio, "sleep", fake_sleep)

    client = SECClient(min_interval=0, max_attempts=2, base_backoff=0.01, max_backoff=0.05)
    payload = await client._get_json("https://data.sec.gov/test")
    assert payload == {"facts": {"us-gaap": {}}}
    assert FakeAsyncClient.calls == 2
    assert sleeps == [0.0]


@pytest.mark.asyncio
async def test_sec_client_does_not_retry_403(monkeypatch):
    FakeAsyncClient.responses = [FakeResponse(403), FakeResponse(200)]
    FakeAsyncClient.calls = 0
    monkeypatch.setattr(sec_module.httpx, "AsyncClient", FakeAsyncClient)
    client = SECClient(min_interval=0, max_attempts=3)

    with pytest.raises(SECForbiddenError):
        await client._get_json("https://data.sec.gov/test")
    assert FakeAsyncClient.calls == 1


@pytest.mark.asyncio
async def test_sec_client_raises_after_rate_limit_retries(monkeypatch):
    FakeAsyncClient.responses = [FakeResponse(429), FakeResponse(429)]
    FakeAsyncClient.calls = 0
    monkeypatch.setattr(sec_module.httpx, "AsyncClient", FakeAsyncClient)
    async def fake_sleep(seconds):
        return None
    monkeypatch.setattr(sec_module.asyncio, "sleep", fake_sleep)

    client = SECClient(min_interval=0, max_attempts=2, base_backoff=0, max_backoff=0)
    with pytest.raises(SECRateLimitError):
        await client._get_json("https://data.sec.gov/test")
    assert FakeAsyncClient.calls == 2


def test_retry_after_supports_seconds_and_http_date():
    assert SECClient._retry_after_seconds("2") == 2.0
    assert SECClient._retry_after_seconds(None) is None


def test_persistent_sec_cache_model_is_registered():
    assert SECProviderCache.__tablename__ == "sec_provider_cache"
    assert "uq_sec_provider_cache_provider_key" in {
        constraint.name for constraint in SECProviderCache.__table__.constraints
    }
