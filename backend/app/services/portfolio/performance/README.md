# Portfolio performance foundation

Increment 5.19.0 adds immutable dated portfolio valuation inputs. A snapshot records invested-asset market value and cash separately; total value is their sum in the portfolio base currency. It also records valuation date, source, methodology, reference, author and server-side recorded timestamp.

## Intended methodology
- TWR requires valuations and external cash-flow amounts with defensible timing. Exact subperiod TWR requires valuation immediately before/after each external flow; daily valuations support daily-linked TWR only with an explicit flow-timing convention.
- MWR/XIRR is a separate investor-experience measure and uses dated external contributions/distributions.
- BUY/SELL and income/cost events are internal portfolio activity, not external investor cash flows. DEPOSIT and WITHDRAWAL are external flows.
- Do not infer portfolio valuation from transaction trade prices or treat deposits/withdrawals as investment return.

## Current limitations
This increment stores and retrieves source-attributed valuations; it does not calculate TWR, MWR/XIRR, P&L, risk or benchmarks. It does not fetch provider data, validate prices, reconcile supplied cash against the ledger, or perform FX conversion. A snapshot is an analyst-supplied input, not independently verified NAV. Multiple observations on one valuation date are allowed; downstream calculations must define a canonical-observation policy.

## Increment 5.20.0 — Daily-boundary TWR

The read-only endpoint `GET /api/v1/portfolio/companies/{company_id}/portfolios/{portfolio_id}/performance/twr?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` calculates geometrically linked TWR from dated valuation snapshots and DEPOSIT/WITHDRAWAL ledger flows. It assumes external flows occur at the start of their trade date and requires a valuation on each non-zero net flow date. It returns 422 when date coverage or capital conditions are insufficient rather than interpolating or estimating. No persisted performance result or schema migration is added.

## Increment 5.20.0 — Daily-boundary TWR

The read-only endpoint `GET /api/v1/portfolio/companies/{company_id}/portfolios/{portfolio_id}/performance/twr?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` calculates geometrically linked TWR from dated valuation snapshots and DEPOSIT/WITHDRAWAL ledger flows. It assumes external flows occur at the start of their trade date and requires a valuation on each non-zero net flow date, as well as on both requested period boundaries. It returns HTTP 422 when date coverage or capital conditions are insufficient rather than interpolating or estimating. No performance result is persisted and no schema migration is added.

## Increment 5.21.0 — Money-weighted return (MWR/XIRR)

The read-only endpoint `GET /api/v1/portfolio/companies/{company_id}/portfolios/{portfolio_id}/performance/mwr?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD` calculates annualized XIRR using actual elapsed days and an ACTUAL/365 convention. The starting NAV is modeled as an investor contribution (negative); DEPOSIT transactions are negative investor cash flows; WITHDRAWAL transactions are positive distributions; ending NAV is a positive terminal distribution. Only DEPOSIT/WITHDRAWAL are external flows; BUY/SELL and income/cost ledger entries remain internal portfolio activity.

The engine selects the latest recorded valuation on each boundary date (greatest id breaks timestamp ties), requires positive start/end NAV and at least one positive and one negative investor flow, and does not require valuations on intermediate flow dates. A bounded log-rate root search rejects missing roots and multiple roots rather than returning an arbitrary result. It uses actual date differences divided by 365, does not interpolate valuations, and does not persist calculated returns. HTTP 422 is returned for insufficient coverage, invalid cash flows, no root or ambiguous roots.

Limitations: no FX, Modified Dietz, benchmark, fee attribution outside the supplied NAV, cash-flow intraday timing, or external data validation. XIRR is sensitive to valuation quality and to the supported search interval (-99.99% to 100000% annualized).
