# Increment 5.18.0 — Portfolio Workspace

## Scope

Deliver the first authenticated frontend for the portfolio transaction ledger and the deterministic positions/cash snapshot introduced in increments 5.16.0 and 5.17.0.

## Changes

- Added `frontend/features/portfolio/portfolio-workspace.tsx`.
- Added route `/portfolio` and linked it from the home page.
- Reused the existing HttpOnly session-cookie, CSRF and refresh flow used by the Valuation Workspace.
- Added company-scoped portfolio listing and creation.
- Added transaction entry for BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAWAL, FEE, TAX and INTEREST.
- Captures trade/settlement dates, asset UUID where required, quantity/unit price or gross amount, fees, taxes, idempotency key, external reference and notes.
- Displays idempotent replays as existing records rather than new writes.
- Added as-of position and cash snapshot view with trade-date/settled balances, unsettled amount, inflows/outflows, net movements, position quantities and gross buy/sell amounts.
- Added ledger history table (latest 100 records), negative-position review warning and limitations.
- Updated Portfolio README and shared frontend styles.

## Safety and limitations

- No edit/delete operations are exposed for immutable ledger entries.
- No schema or migration changes.
- No Neon, production database or deployment operations.
- FX, cost basis, realized/unrealized P&L, broker statement reconciliation, corporate actions, performance and backtesting remain out of scope.
- Portfolio cash is ledger-derived and is not a bank/broker statement reconciliation.
- Asset UUIDs must belong to the selected company; the backend enforces ownership.
- Transaction currency must match the portfolio base currency.

## Validation

CI validation is pending on the pull request. No local test execution is claimed.

## Review status

This increment is submitted for review. Do not merge until the user explicitly decides to do so.
