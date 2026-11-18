# Portfolio Workspace

The workspace provides a tenant-scoped append-only transaction ledger and read-only positions/cash reconciliation. Increment 5.19.0 adds backend valuation snapshot inputs (dated market value, cash value, source and methodology); no performance metric is displayed until valuation and external-flow coverage supports a defensible methodology.

Increment 5.21.0 adds a read-only backend MWR/XIRR calculation endpoint. The current workspace does not yet expose a performance UI; this endpoint is available to authenticated company-scoped API clients. No frontend calculation or investment recommendation is made.
