# Valuation

The Valuation Workspace is available at `/valuation`.

- Uses the authenticated, company-scoped FCFF DCF API.
- Requires the analyst to provide the company UUID and complete Bear/Base/Bull forecast assumptions as JSON.
- Displays per-share values, enterprise values, Base-case WACC/terminal-growth sensitivity and model warnings.
- Loads and displays persisted valuation history.
- Opens immutable valuation run details from history, showing metadata, original assumptions and the complete persisted result without recalculation.
- Compares two persisted valuation runs directly from the workspace, showing absolute and percentage deltas for Bear/Base/Bull metrics.
- Lists assumption changes down to nested scenario and forecast-period paths, including previous/new values and whether a value was added or removed.
- The comparison is read-only, does not recalculate snapshots and requires analyst review.
- Does not infer assumptions, fetch market prices or issue investment recommendations.
