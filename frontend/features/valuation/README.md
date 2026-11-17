# Valuation

The Valuation Workspace is available at `/valuation`.

- Uses the authenticated, company-scoped FCFF DCF API.
- Requires the analyst to provide the company UUID and complete Bear/Base/Bull forecast assumptions as JSON.
- Displays per-share values, enterprise values, Base-case WACC/terminal-growth sensitivity and model warnings.
- Loads and displays persisted valuation history.
- Does not infer assumptions, fetch market prices or issue investment recommendations.
