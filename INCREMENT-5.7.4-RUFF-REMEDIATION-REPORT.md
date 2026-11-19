# Increment 5.7.4 — Ruff remediation report

## Base version

Based on `market-analytics-increment-5.7.3-ruff-fixes.zip` and the Ruff diagnostic file supplied in the conversation (371 reported diagnostics across 69 source/test files).

## Changes applied

- Replaced integer-string `Decimal("N")` constructors with exact integer constructors `Decimal(N)`; decimal-string constants such as `Decimal("0.01")` remain unchanged.
- Replaced `timezone.utc` with `datetime.UTC` and updated the corresponding imports (Python requirement is >=3.12).
- Changed `re.IGNORECASE` to the equivalent `re.I`.
- Scoped Ruff `B008` ignore to FastAPI API modules, where `Depends(...)` in parameter defaults is the framework's dependency-injection pattern.
- Fixed the loop-variable capture in financial quarter derivation by binding the current group to the nested helper's default argument.
- Removed confirmed unused local assignments and imports; removed duplicate model imports.
- Replaced adjacent-pair `zip(sequence, sequence[1:])` loops with `itertools.pairwise`.
- Applied other targeted fixes for the reported `UP035`, `F401`, `F841`, `F811`, `RUF012`, `RUF007`, `B009`, `FLY002`, `RET501`, `PLR1711`, and `B017` findings.

## Validation performed

- `python -m compileall` over `backend/app` and `backend/tests`: passed.
- `pytest tests/unit` excluding `tests/unit/test_dependencies.py`: **180 passed**.
- Full unit collection was also attempted; it stopped because the environment does not have `asyncpg` installed (`ModuleNotFoundError`).
- Ruff itself could not be installed or executed in this environment because there is no network access and no Ruff executable is present.

## Outstanding limitation

This is a remediation build, **not a certified Ruff-clean build**. The original diagnostics include import-order (`I001`) findings across many modules. Those import blocks have not all been reformatted, and Ruff could not be rerun to establish the exact remaining diagnostic count. Run the project's configured Ruff command in the backend environment after installing the declared development dependency. Do not treat this ZIP as having passed Ruff until that check succeeds.

## Scope preserved

No financial formulas, SEC source records, filing/accession lineage, restatement history, database migrations, Neon settings, or production database configuration were intentionally changed. No global investment score was introduced.
