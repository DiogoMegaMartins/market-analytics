# Portfolio

Increment 5.16.0 implements tenant-scoped portfolio containers and an append-only transaction ledger.

- Supported entries: BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAWAL, FEE, TAX and INTEREST.
- Every entry stores trade date, optional settlement date, original amount/currency, fees, taxes, source reference and an idempotency key.
- BUY/SELL require an existing asset reference, positive quantity and price, and exact gross amount arithmetic.
- Transaction currency must match the portfolio base currency in this increment; FX conversion is intentionally deferred.
- The ledger is append-only at the PostgreSQL layer. Corrections must be represented by future compensating entries, not mutation or deletion.
- Portfolio and transaction reads/writes are company-membership scoped.

Not yet implemented: positions, lot accounting (FIFO/average/specific lots), cash reconciliation, corporate actions, FX, TWR/MWR, risk and backtesting. No investment recommendation is produced.
