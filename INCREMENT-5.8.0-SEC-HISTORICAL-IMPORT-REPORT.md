# Market Analytics — Increment 5.8.0

## Scope

Introduces the first controlled orchestration layer for the historical SEC Company Facts import. It builds import targets for the five approved research-universe tickers (MSFT, KO, COST, CAT and XOM) from **existing company UUIDs supplied by the caller**. It does not create company records, resolve or guess UUIDs, or connect to a database by itself.

The orchestrator validates ticker/CIK pairs against the fixed allowlist, rejects duplicate tickers and company IDs, processes issuers sequentially, captures a per-issuer result, and rolls back the session after an issuer-level exception before continuing to the next issuer. Successful imports continue to use the existing `SECCompanyFactsImportService`, which persists the raw SEC payload, reported facts, normalized facts and direct-source lineage.

## Target mapping

| Ticker | CIK |
|---|---:|
| MSFT | 0000789019 |
| KO | 0000021344 |
| COST | 0000909832 |
| CAT | 0000018230 |
| XOM | 0000034088 |

The caller must supply the already-existing `company_id` values. Partial target sets are supported.

## Validation

- `python -m compileall -q app tests`: passed.
- `pytest -q --ignore=tests/unit/test_dependencies.py`: **197 passed, 9 skipped**.
- Full `pytest -q`: **197 passed, 9 skipped, 1 failed**. The sole failure is the existing dependency-import test because `asyncpg` is not installed in the execution environment (`ModuleNotFoundError`).
- Ruff was not available in the local execution environment; no Ruff-clean claim is made.

## Operational boundaries

- No database connection or write was performed while preparing this increment.
- No Alembic migration or schema change was added.
- No production or integration Neon branch was modified.
- No financial calculations, metric definitions, or SEC source records were changed.
- The orchestrator is code-only. A controlled integration-branch run still requires the caller to resolve existing company UUIDs and deliberately invoke `import_targets` using a dedicated integration session.
- `SECCompanyFactsImportService` commits during import; do not call the orchestrator inside a larger transaction containing unrelated pending work.

## Example

```python
company_ids = {
    "MSFT": existing_msft_company_uuid,
    "KO": existing_ko_company_uuid,
    "COST": existing_cost_company_uuid,
    "CAT": existing_cat_company_uuid,
    "XOM": existing_xom_company_uuid,
}
targets = build_default_sec_targets(company_ids)
results = await SECHistoricalImportOrchestrator().import_targets(integration_session, targets)
```

Review each result status and details before moving on to historical metric reconciliation.
