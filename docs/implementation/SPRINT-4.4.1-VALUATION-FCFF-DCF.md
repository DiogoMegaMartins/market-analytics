# Sprint 4.4.1 — FCFF DCF Valuation Engine v1

## Objective

Introduce a deterministic, pure FCFF DCF calculation primitive with explicit Bear/Base/Bull assumptions, transparent cash-flow derivation, a Base-case sensitivity grid and a terminal-value concentration warning.

## Formula

For each forecast year:

- EBIT = Revenue × EBIT margin
- NOPAT = EBIT × (1 − tax rate)
- FCFF = NOPAT + D&A − CAPEX − change in net working capital
- Present value of FCFF = FCFF / (1 + WACC)^period
- Terminal value = final forecast FCFF × (1 + terminal growth) / (WACC − terminal growth)
- Enterprise value = present value of explicit FCFF + present value of terminal value
- Equity value = enterprise value − net debt
- Value per share = equity value / diluted shares

## Contract and safeguards

- Requires exactly three scenarios: BEAR, BASE and BULL.
- Each scenario has 1–10 consecutive forecast periods, with identical year coverage.
- Currency is an explicit three-letter uppercase code; all monetary inputs must share the same currency and scale.
- WACC must be between zero and one; terminal growth must be greater than -100% and lower than WACC.
- Tax rates must be between zero and one. D&A and CAPEX are non-negative magnitudes. Change in NWC is signed.
- All numeric inputs must be finite. Diluted shares must be positive.
- A present-value terminal contribution above 80% of positive enterprise value generates a warning only.
- No market price, peer multiple, forecast, tax rate, capital structure or other assumption is fetched or inferred.
- The result is not an investment recommendation and requires analyst review.

## Scope limitations

This increment adds the pure calculation engine and unit tests only. It does not add database persistence, API endpoints, valuation history, market-price comparison, point-in-time source lineage, or sector-specific valuation models. FCFF DCF must not be applied to banks, insurers or REITs; those require the methods in docs/methodology/07_VALUATION.md.

## Validation

Unit tests are added for the FCFF formula, scenario ordering, sensitivity output, invalid assumptions, non-finite values and terminal-value concentration warning. CI is the authoritative execution environment for this increment.
