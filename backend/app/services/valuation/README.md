# Valuation

## FCFF DCF v1

The `app/services/valuation/dcf.py` module provides a pure deterministic FCFF discounted-cash-flow calculation.

- Inputs are explicit Bear/Base/Bull forecast drivers, WACC, terminal growth, net debt, diluted shares, base year and currency.
- FCFF is calculated as EBIT × (1 − tax rate) + D&A − CAPEX − change in NWC.
- The output includes enterprise value, equity value, value per diluted share, terminal-value concentration warnings and a Base-case WACC/terminal-growth sensitivity grid.
- Missing, non-finite, inconsistent or invalid assumptions are rejected; no missing values are imputed.
- All monetary inputs must share one currency and scale.
- The company-scoped API persists each calculation as an immutable valuation run, including the explicit input assumptions and versioned result. The history endpoint returns prior runs.
- No prices, market assumptions or forecasts are retrieved or inferred automatically; no investment recommendation is issued.

Banks, insurers, REITs and other specialist sectors must not use this FCFF implementation without a sector-appropriate valuation method. Every output requires analyst review.
