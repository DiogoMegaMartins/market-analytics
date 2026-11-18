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

## Valuation run comparison

The pure `app/services/valuation/comparison.py` service compares two persisted immutable snapshots without recalculating either valuation. It requires matching method, engine version, base year and currency, reports Bear/Base/Bull deltas for enterprise value, equity value, value per share and present-value components, and lists changed top-level assumption fields. It also recursively reports each changed nested assumption using an RFC 6901 JSON Pointer (`json_pointer`) as the canonical unambiguous path, alongside the legacy dotted `path`, previous and new JSON values, and explicit presence flags to distinguish additions/removals from JSON null. Percentage deltas are null for a zero baseline. The company-scoped API never exposes a run belonging to another company. Comparisons are review aids, not investment recommendations.
