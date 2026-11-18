# Portfolio

Increment 5.16.0 implements tenant-scoped portfolio containers and an append-only transaction ledger.

Increment 5.17.0 adds deterministic, read-only snapshots:
- Net asset quantities derived from BUY and SELL entries by trade date.
- Trade-date and settlement-date cash balances, with trade-date fallback if settlement date is absent.
- Cash movement totals by transaction type, including fees and taxes.
- Negative holdings are preserved and flagged for analyst review; no automatic correction is made.
- No lot accounting, cost basis, realized/unrealized P&L, FX, corporate actions, or broker/bank statement reconciliation is inferred.

Every API access remains company scoped. Asset references supplied for new transactions must belong to the same company as the portfolio.
