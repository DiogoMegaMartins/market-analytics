"""Bounded SEC filing download and deterministic text/section extraction.

Extracted passages are candidates for analyst review, never scored evidence.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from hashlib import sha256
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlparse

from app.providers.sec.client import SECClient, SECProviderError

MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
ALLOWED_HOSTS = {"www.sec.gov", "sec.gov"}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag in {"script", "style", "ix:header"} or attrs_dict.get("aria-hidden") == "true":
            self.hidden += 1
        elif tag in {"p", "div", "tr", "td", "th", "br", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "ix:header"} and self.hidden:
            self.hidden -= 1
        elif tag in {"p", "div", "tr", "td", "th", "h1", "h2", "h3"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


def extract_plain_text(content: bytes, content_type: str = "text/html") -> str:
    text = content.decode("utf-8", errors="replace")
    if "html" in content_type.lower() or re.search(r"<\s*(html|body|div|ix:)", text[:5000], re.IGNORECASE):
        parser = _TextExtractor()
        parser.feed(text)
        text = "".join(parser.parts)
    text = text.replace("\xa0", " ").replace("\u200b", "")
    lines = [re.sub(r"[\t \r]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


SECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("BUSINESS", re.compile(r"\bITEM\s+1\.?\s+BUSINESS\b", re.IGNORECASE)),
    ("RISK_FACTORS", re.compile(r"\bITEM\s+1A\.?\s+RISK\s+FACTORS\b", re.IGNORECASE)),
    ("MD_AND_A", re.compile(r"\bITEM\s+7\.?\s+MANAGEMENT.{0,30}DISCUSSION", re.IGNORECASE)),
    ("FINANCIAL_STATEMENTS", re.compile(r"\bITEM\s+8\.?\s+FINANCIAL\s+STATEMENTS", re.IGNORECASE)),
)


def extract_sections(text: str) -> list[dict[str, Any]]:
    hits: list[tuple[int, str]] = []
    for name, pattern in SECTION_PATTERNS:
        match = pattern.search(text)
        if match:
            hits.append((match.start(), name))
    hits.sort()
    result = []
    for index, (start, name) in enumerate(hits):
        end = hits[index + 1][0] if index + 1 < len(hits) else len(text)
        passage = text[start:end].strip()
        if passage:
            result.append({"section": name, "start_offset": start, "end_offset": end,
                           "text": passage})
    return result


@dataclass(frozen=True)
class FilingDocument:
    url: str
    content_type: str
    byte_count: int
    sha256: str
    text: str
    sections: tuple[dict[str, Any], ...]
    extraction_version: str = "SEC_TEXT_1.0.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SECFilingDocumentService:
    def __init__(self, client: SECClient | None = None, *, max_bytes: int = MAX_DOCUMENT_BYTES):
        self.client = client or SECClient()
        self.max_bytes = max_bytes

    async def download_and_extract(self, url: str) -> FilingDocument:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
            raise ValueError("Only HTTPS SEC filing URLs are allowed")
        if not parsed.path.startswith("/Archives/edgar/data/"):
            raise ValueError("URL is not an SEC EDGAR archive document")
        response = await self.client._get_response(url)
        content = response.content
        if len(content) > self.max_bytes:
            raise ValueError("SEC filing exceeds configured maximum document size")
        if not content:
            raise SECProviderError("SEC returned an empty filing document")
        content_type = response.headers.get("content-type", "application/octet-stream")
        text = extract_plain_text(content, content_type)
        if not text.strip():
            raise ValueError("No extractable text found in SEC filing")
        return FilingDocument(url=url, content_type=content_type,
            byte_count=len(content), sha256=sha256(content).hexdigest(),
            text=text, sections=tuple(extract_sections(text)))
