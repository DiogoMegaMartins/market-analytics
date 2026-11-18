# Portfolio performance foundation

Increment 5.19.0 adds immutable dated portfolio valuation inputs. A snapshot records invested-asset market value and cash separately; total value is their sum in the portfolio base currency. It also records valuation date, source, methodology, reference, author and server-side recorded timestamp.

## Intended methodology
- TWR requires valuations and external cash-flow amounts with defensible timing. Exact subperiod TWR requires valuation immediately before/after each external flow; daily valuations support daily-linked TWR only with an explicit flow-timing convention.
- MWR/XIRR is a separate investor-experience measure and uses dated external contributions/distributions.
- BUY/SELL and income/cost events are internal portfolio activity, not external investor cash flows. DEPOSIT and WITHDRAWAL are external flows.
- Do not infer portfolio valuation from transaction trade prices or treat deposits/withdrawals as investment return.

## Current limitations
This increment stores and retrieves source-attributed valuations; it does not calculate TWR, MWR/XIRR, P&L, risk or benchmarks. It does not fetch provider data, validate prices, reconcile supplied cash against the ledger, or perform FX conversion. A snapshot is an analyst-supplied input, not independently verified NAV. Multiple observations on one valuation date are allowed; downstream calculations must define a canonical-observation policy.
