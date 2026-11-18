# Portfolio

## Increment 5.16.0 — Transaction ledger

Company-scoped portfolio containers and an append-only transaction ledger. Supported types: BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAWAL, FEE, TAX and INTEREST. Idempotency keys prevent duplicate writes. Transactions use the portfolio base currency; FX is not enabled.

## Increment 5.17.0 — Positions and cash snapshot

Read-only endpoint:

`GET /api/v1/portfolio/companies/{company_id}/portfolios/{portfolio_id}/positions?as_of=YYYY-MM-DD`

Holdings are net BUY/SELL quantities by trade date. Cash includes trade-date and settlement-date views, with settlement_date falling back to trade_date. Negative positions are preserved and flagged REVIEW_REQUIRED.

## Increment 5.18.0 — Portfolio Workspace

The authenticated Next.js workspace is available at `/portfolio` and linked from the home page. It supports:

- Listing company-scoped portfolios and creating a portfolio with a base currency.
- Recording all supported transaction types with trade/settlement dates, asset reference, quantity/price or gross amount, fees, taxes, external reference and notes.
- Sending an explicit idempotency key and displaying idempotent replays.
- Loading up to 100 ledger transactions and an as-of positions/cash snapshot.
- Displaying net quantities, bought/sold quantities and gross buy/sell amounts by asset.
- Displaying trade-date cash, settled cash, unsettled net amount, inflows/outflows and net movements by transaction type.
- Flagging negative holdings for analyst review and exposing calculation limitations.

The UI uses the existing HttpOnly session-cookie and CSRF flow. It does not edit/delete ledger entries, calculate cost basis or P&L, reconcile against broker statements, apply FX/corporate actions, calculate performance or backtest. No database schema or migration changes were introduced in 5.18.0.
