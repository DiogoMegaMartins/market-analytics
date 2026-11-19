# Financial Metrics Engine v1

The first implementation calculates annual operating margin, net margin, OCF margin,
FCF, FCF margin and revenue growth. It uses `Decimal` and consumes only annual
`NormalizedFinancialFact` records. Metric runs, results, lineage and quality findings
are append-only and versioned by `financial-metrics-v1.0`.

CAPEX is required as a positive magnitude. Negative values are not converted with
`abs()`; FCF is marked invalid until an explicit, versioned source-sign normalization
is implemented. Currency, unit, period and duplicate-metric conflicts block affected
calculations. Missing inputs remain unavailable rather than being treated as zero.

Quarter derivation is separately versioned as `quarter-derivation-v1.0`:

- Q2 = Q2 YTD - Q1
- Q3 = Q3 YTD - Q2 YTD
- Q4 = FY - Q3 YTD

Derivations require matching company, metric, fiscal year, unit and currency. They are
stored as `DERIVED` normalized observations and link to both source facts. Reported
observations are never overwritten. The derivation endpoint currently resolves the
latest available inputs; point-in-time derivation policy is a follow-up requirement.

The initial quality rules are intentionally conservative. They flag duplicate periods,
unit/currency/period mismatches and unexpected CAPEX signs. This is not yet a complete
accounting-quality scoring model and does not claim to detect fraud or accounting
manipulation.
