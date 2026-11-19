from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.financial_data.sec_company_facts import SECCompanyFactsImportService


class CacheHitSession:
    def __init__(self, cached):
        self.cached = cached
    async def scalar(self, statement):
        return self.cached
    async def commit(self):
        pass


class CacheMissSession:
    def __init__(self):
        self.executed = []
    async def scalar(self, statement):
        return None
    async def commit(self):
        pass
    async def execute(self, statement):
        self.executed.append(statement)


class NeverCallSEC:
    COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    async def company_facts(self, cik):
        raise AssertionError("cache hit must not call SEC")


class FakeSEC:
    COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    async def company_facts(self, cik):
        import json
        from hashlib import sha256
        body = json.dumps({"facts": {"us-gaap": {}}})
        return {"facts": {"us-gaap": {}}}, body, sha256(body.encode()).hexdigest()


@pytest.mark.asyncio
async def test_company_facts_import_uses_unexpired_persistent_cache():
    now = datetime.now(UTC)
    cached = SimpleNamespace(
        payload_text='{"facts":{"us-gaap":{}}}',
        payload_hash="a" * 64,
        fetched_at=now - timedelta(minutes=2),
    )
    service = SECCompanyFactsImportService(NeverCallSEC())
    payload, raw, digest, fetched_at, cache_hit = await service._get_payload(
        CacheHitSession(cached), cik="0000789019",
        source_url="https://data.sec.gov/companyfacts",
    )
    assert payload == {"facts": {"us-gaap": {}}}
    assert raw == cached.payload_text
    assert digest == cached.payload_hash
    assert fetched_at == cached.fetched_at
    assert cache_hit is True


@pytest.mark.asyncio
async def test_company_facts_import_writes_cache_on_miss():
    session = CacheMissSession()
    service = SECCompanyFactsImportService(FakeSEC())
    payload, _raw, digest, _fetched_at, cache_hit = await service._get_payload(
        session, cik="0000789019", source_url="https://data.sec.gov/companyfacts",
    )
    assert payload == {"facts": {"us-gaap": {}}}
    assert digest and len(digest) == 64
    assert cache_hit is False
    assert len(session.executed) == 1
