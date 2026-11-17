from hashlib import sha256
from typing import ClassVar

import pytest

from app.services.business_quality.filing_documents import (
    SECFilingDocumentService,
    extract_plain_text,
    extract_sections,
)


def test_html_text_extraction_omits_scripts_and_normalizes():
    result = extract_plain_text(b"<html><script>secret()</script><p>Hello&nbsp;world</p></html>")
    assert "Hello world" in result
    assert "secret" not in result


def test_sections_are_extracted_with_offsets():
    text = "ITEM 1. BUSINESS\nBusiness text\nITEM 1A. RISK FACTORS\nRisk text"
    sections = extract_sections(text)
    assert [item["section"] for item in sections] == ["BUSINESS", "RISK_FACTORS"]
    assert sections[0]["text"].startswith("ITEM 1. BUSINESS")


@pytest.mark.asyncio
async def test_rejects_non_sec_or_non_https_urls():
    service = SECFilingDocumentService()
    with pytest.raises(ValueError):
        await service.download_and_extract("https://example.com/Archives/edgar/data/a.htm")
    with pytest.raises(ValueError):
        await service.download_and_extract("http://www.sec.gov/Archives/edgar/data/a.htm")


@pytest.mark.asyncio
async def test_download_extracts_and_hashes_document():
    class Response:
        content = b"<html><body><p>ITEM 1. BUSINESS</p><p>Durable demand</p></body></html>"
        headers: ClassVar[dict[str, str]] = {"content-type": "text/html"}
    class Client:
        async def _get_response(self, url):
            return Response()
    result = await SECFilingDocumentService(Client()).download_and_extract(
        "https://www.sec.gov/Archives/edgar/data/1/abc/report.htm")
    assert result.sha256 == sha256(Response.content).hexdigest()
    assert result.byte_count == len(Response.content)
    assert result.sections[0]["section"] == "BUSINESS"
