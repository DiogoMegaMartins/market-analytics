"""SEC filing catalogue for historical Business Quality research.

This module indexes filing metadata and document URLs; it does not claim that
filing text has been downloaded, parsed, or converted into scored evidence.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import date
from hashlib import sha256
from typing import Any

from app.providers.sec.client import SECClient


@dataclass(frozen=True)
class SECFilingRecord:
    cik: str
    accession_number: str
    form: str
    filing_date: date
    report_date: date | None
    acceptance_datetime: str | None
    primary_document: str
    filing_url: str
    primary_document_url: str
    source: str = "SEC_SUBMISSIONS"

    @property
    def record_hash(self) -> str:
        payload = f"{self.cik}|{self.accession_number}|{self.form}|{self.filing_date.isoformat()}|{self.primary_document}"
        return sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["filing_date"] = self.filing_date.isoformat()
        result["report_date"] = self.report_date.isoformat() if self.report_date else None
        result["record_hash"] = self.record_hash
        return result


def _date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def parse_submission_rows(payload: dict[str, Any], *, cik: str,
                          forms: Iterable[str] = ("10-K", "10-Q", "20-F", "6-K"),
                          filed_from: date | None = None,
                          filed_to: date | None = None) -> list[SECFilingRecord]:
    recent = payload.get("filings", {}).get("recent", {})
    if not isinstance(recent, dict):
        return []
    allowed = set(forms)
    fields = ("accessionNumber", "filingDate", "reportDate", "acceptanceDateTime", "form", "primaryDocument")
    lengths = [len(recent.get(field, [])) for field in fields]
    if not lengths or len(set(lengths)) != 1:
        raise ValueError("SEC submissions recent arrays have inconsistent lengths")
    padded = SECClient.normalize_cik(cik)
    records: list[SECFilingRecord] = []
    for row in zip(*(recent[field] for field in fields)):
        accession, filed, report, accepted, form, document = row
        filing_date = _date(filed)
        if form not in allowed or filing_date is None or not accession or not document:
            continue
        if filed_from and filing_date < filed_from or filed_to and filing_date > filed_to:
            continue
        accession_nodash = str(accession).replace("-", "")
        if not accession_nodash.isdigit() or "/" in str(document) or ".." in str(document):
            continue
        base = f"https://www.sec.gov/Archives/edgar/data/{int(padded)}/{accession_nodash}"
        records.append(SECFilingRecord(
            cik=padded, accession_number=str(accession), form=str(form),
            filing_date=filing_date, report_date=_date(report),
            acceptance_datetime=str(accepted) if accepted else None,
            primary_document=str(document), filing_url=f"{base}/",
            primary_document_url=f"{base}/{document}",
        ))
    return sorted(records, key=lambda item: (item.filing_date, item.accession_number))


class SECFilingCatalogueService:
    def __init__(self, client: SECClient | None = None) -> None:
        self.client = client or SECClient()

    async def collect(self, *, cik: str, filed_from: date | None = None,
                      filed_to: date | None = None,
                      forms: Iterable[str] = ("10-K", "10-Q", "20-F", "6-K")) -> dict[str, Any]:
        padded = self.client.normalize_cik(cik)
        index = await self.client.submissions(padded)
        records = parse_submission_rows(index, cik=padded, forms=forms,
                                        filed_from=filed_from, filed_to=filed_to)
        shards: list[str] = []
        # SEC submissions index links older filing shards; fetch only those whose
        # date ranges overlap the requested historical window.
        for shard in index.get("filings", {}).get("files", []):
            name = shard.get("name")
            start, end = _date(shard.get("filingFrom")), _date(shard.get("filingTo"))
            if not name or (filed_from and end and end < filed_from) or (filed_to and start and start > filed_to):
                continue
            payload = await self.client.submissions_file(str(name))
            records.extend(parse_submission_rows(payload, cik=padded, forms=forms,
                                                 filed_from=filed_from, filed_to=filed_to))
            shards.append(str(name))
        unique = {record.accession_number: record for record in records}
        ordered = sorted(unique.values(), key=lambda item: (item.filing_date, item.accession_number))
        return {
            "cik": padded, "source": "SEC_EDGAR_SUBMISSIONS",
            "collection_scope": {"filed_from": filed_from.isoformat() if filed_from else None,
                                  "filed_to": filed_to.isoformat() if filed_to else None,
                                  "forms": sorted(set(forms))},
            "shards_fetched": shards,
            "filing_count": len(ordered),
            "filings": [record.to_dict() for record in ordered],
            "limitations": ["Metadata catalogue only; filing contents are not downloaded or parsed.",
                            "Filing date is not a substitute for verified public availability timestamp."],
        }
