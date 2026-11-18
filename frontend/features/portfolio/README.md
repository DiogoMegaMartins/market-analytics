# Portfolio Workspace

The workspace provides a tenant-scoped append-only transaction ledger, read-only positions/cash reconciliation, and a read-only performance view.

Increment 5.22.0 exposes the existing backend TWR and MWR/XIRR endpoints in the portfolio workspace. Users select a date range and the UI requests both metrics independently. It displays observed NAV boundary values from the TWR subperiods; it does not interpolate daily NAV or calculate metrics in the browser.

Missing valuation coverage, invalid periods, and unsupported/ambiguous calculations remain explicit unavailable states. The UI never estimates missing valuations or substitutes zero returns. TWR requires a starting and ending valuation plus a valuation on each non-zero external cash-flow date. XIRR uses ACTUAL/365 and rejects missing or ambiguous roots.

No backend schema, calculation engine, transaction behavior, or production data is changed by this increment.
