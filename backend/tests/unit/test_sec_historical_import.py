from uuid import uuid4

import pytest

from app.orchestration.sec_historical_import import (
    SEC_HISTORICAL_UNIVERSE,
    SECHistoricalImportOrchestrator,
    SECHistoricalImportTarget,
    build_default_sec_targets,
)


class FakeSession:
    def __init__(self) -> None:
        self.rollbacks = 0

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeImporter:
    def __init__(self, failures: set[str] | None = None) -> None:
        self.failures = failures or set()
        self.calls: list[str] = []

    async def import_company(self, session, *, company_id, cik):
        ticker = next(key for key, value in SEC_HISTORICAL_UNIVERSE.items() if value == cik)
        self.calls.append(ticker)
        if ticker in self.failures:
            raise RuntimeError("provider unavailable")
        return {"company_id": str(company_id), "cik": cik, "imported_facts": 12}


def test_build_default_targets_uses_only_existing_company_ids() -> None:
    company_id = uuid4()
    targets = build_default_sec_targets({"MSFT": company_id, "KO": uuid4()})

    assert [target.ticker for target in targets] == ["MSFT", "KO"]
    assert targets[0].cik == "0000789019"
    assert targets[0].company_id == company_id


def test_build_default_targets_rejects_unknown_ticker() -> None:
    with pytest.raises(ValueError, match="Unsupported SEC universe"):
        build_default_sec_targets({"UNKNOWN": uuid4()})


@pytest.mark.asyncio
async def test_orchestrator_imports_sequentially_and_returns_details() -> None:
    session = FakeSession()
    importer = FakeImporter()
    targets = build_default_sec_targets({"MSFT": uuid4(), "KO": uuid4()})

    results = await SECHistoricalImportOrchestrator(importer).import_targets(session, targets)

    assert importer.calls == ["MSFT", "KO"]
    assert [result.status for result in results] == ["IMPORTED", "IMPORTED"]
    assert results[0].details["imported_facts"] == 12
    assert session.rollbacks == 0


@pytest.mark.asyncio
async def test_orchestrator_isolates_failure_and_continues() -> None:
    session = FakeSession()
    importer = FakeImporter(failures={"MSFT"})
    targets = build_default_sec_targets({"MSFT": uuid4(), "KO": uuid4()})

    results = await SECHistoricalImportOrchestrator(importer).import_targets(session, targets)

    assert importer.calls == ["MSFT", "KO"]
    assert [result.status for result in results] == ["FAILED", "IMPORTED"]
    assert results[0].error_type == "RuntimeError"
    assert session.rollbacks == 1


@pytest.mark.asyncio
async def test_orchestrator_rejects_duplicate_ticker() -> None:
    company_id = uuid4()
    target = SECHistoricalImportTarget("MSFT", SEC_HISTORICAL_UNIVERSE["MSFT"], company_id)
    with pytest.raises(ValueError, match="duplicate tickers"):
        await SECHistoricalImportOrchestrator(FakeImporter()).import_targets(
            FakeSession(), [target, target],
        )


@pytest.mark.asyncio
async def test_orchestrator_rejects_unapproved_ticker_cik_pair() -> None:
    target = SECHistoricalImportTarget("MSFT", SEC_HISTORICAL_UNIVERSE["KO"], uuid4())
    with pytest.raises(ValueError, match="not in the approved SEC universe"):
        await SECHistoricalImportOrchestrator(FakeImporter()).import_targets(
            FakeSession(), [target],
        )
