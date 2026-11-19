from datetime import date

import pytest

from app.services.business_quality.sec_filings import (
    SECFilingCatalogueService,
    parse_submission_rows,
)


def payload():
    return {"filings": {"recent": {
        "accessionNumber": ["0000789019-23-000010", "0000789019-24-000020", "0000789019-24-000030"],
        "filingDate": ["2023-07-27", "2024-02-02", "2024-04-25"],
        "reportDate": ["2023-07-01", "2023-12-31", "2024-03-31"],
        "acceptanceDateTime": ["20230727160000", "20240202160000", "20240425160000"],
        "form": ["10-K", "10-K", "10-Q"],
        "primaryDocument": ["a.htm", "b.htm", "c.htm"],
    }, "files": []}}


def test_parse_sec_filings_and_construct_archive_urls():
    rows = parse_submission_rows(payload(), cik="789019")
    assert len(rows) == 3
    assert rows[0].cik == "0000789019"
    assert rows[0].filing_date == date(2023, 7, 27)
    assert rows[0].primary_document_url.endswith("/a.htm")
    assert len(rows[0].record_hash) == 64


def test_filter_by_filing_date_and_form():
    rows = parse_submission_rows(payload(), cik="789019", forms=("10-K",),
                                 filed_from=date(2024, 1, 1))
    assert len(rows) == 1 and rows[0].accession_number.endswith("000020")


def test_inconsistent_sec_arrays_rejected():
    data = payload()
    data["filings"]["recent"]["form"].pop()
    with pytest.raises(ValueError, match="inconsistent"):
        parse_submission_rows(data, cik="789019")


@pytest.mark.asyncio
async def test_catalogue_collects_recent_and_historical_shards():
    class Client:
        def normalize_cik(self, cik): return str(cik).zfill(10)
        async def submissions(self, cik):
            data = payload()
            data["filings"]["files"] = [{"name": "old.json", "filingFrom": "2010-01-01", "filingTo": "2012-12-31"}]
            return data
        async def submissions_file(self, name):
            return {"filings": {"recent": {k: [v[0]] for k, v in {
                "accessionNumber": ["0000789019-11-000001"], "filingDate": ["2011-02-01"],
                "reportDate": ["2010-12-31"], "acceptanceDateTime": ["20110201120000"],
                "form": ["10-K"], "primaryDocument": ["old.htm"]}.items()}}}
    result = await SECFilingCatalogueService(Client()).collect(
        cik="789019", filed_from=date(2010, 1, 1), filed_to=date(2012, 12, 31), forms=("10-K",))
    assert result["filing_count"] == 1
    assert result["shards_fetched"] == ["old.json"]
