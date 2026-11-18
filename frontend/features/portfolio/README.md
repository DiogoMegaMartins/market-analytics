# Portfolio

Backend API foundation delivered in Increment 5.16.0: company-scoped portfolio containers and append-only transaction ledger.

Increment 5.17.0 exposes a read-only positions and ledger-cash snapshot through:
`GET /api/v1/portfolio/companies/{company_id}/portfolios/{portfolio_id}/positions?as_of=YYYY-MM-DD`.

A frontend transaction-entry and positions workspace remains pending. Positions are derived from BUY/SELL quantities; cash is ledger-derived and is not a bank/broker statement reconciliation. Cost basis, performance, FX and backtesting are not included.
