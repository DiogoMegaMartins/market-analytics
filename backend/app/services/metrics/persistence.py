from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fact_resolution import ResolutionPolicy
from app.models.financial_data import (
    FinancialMetricLineage,
    FinancialMetricResult,
    FinancialMetricRun,
    FinancialQualityFinding,
    NormalizedFinancialFact,
)
from app.services.metrics.calculator import (
    METRICS_VERSION,
    calculate_annual_metrics,
    calculate_growth,
)
from app.services.metrics.quality import validate_fact_set


class FinancialMetricsService:
    async def calculate_annual(
        self, session: AsyncSession, *, company_id: UUID, fiscal_year: int,
        policy: ResolutionPolicy = ResolutionPolicy.LATEST_RESTATED,
        as_known_at: date | None = None,
    ) -> dict:
        if policy == ResolutionPolicy.AS_KNOWN_AT and as_known_at is None:
            raise ValueError("AS_KNOWN_AT requires as_known_at")
        stmt = select(NormalizedFinancialFact).where(
            NormalizedFinancialFact.company_id == company_id,
            NormalizedFinancialFact.fiscal_year == fiscal_year,
            NormalizedFinancialFact.period_kind == "ANNUAL",
        )
        rows = list((await session.scalars(stmt)).all())
        if policy == ResolutionPolicy.AS_KNOWN_AT:
            rows = [row for row in rows if row.filed_at is not None and row.filed_at <= as_known_at]
        # Select the latest filing per metric/unit/currency. Never merge currencies or units.
        grouped: dict[tuple, list[NormalizedFinancialFact]] = {}
        for row in rows:
            grouped.setdefault((row.metric_id, row.unit, row.currency), []).append(row)
        selected: list[NormalizedFinancialFact] = []
        for candidates in grouped.values():
            candidates.sort(key=lambda item: (item.filed_at or date.min, item.available_at), reverse=True)
            selected.append(candidates[0])

        findings = validate_fact_set(selected)
        by_metric: dict[str, NormalizedFinancialFact] = {}
        duplicates = {finding.metric_id for finding in findings if finding.rule_id == "DUPLICATE_PERIOD"}
        for row in selected:
            if row.metric_id not in by_metric:
                by_metric[row.metric_id] = row
            else:
                duplicates.add(row.metric_id)
        blocked = any(f.severity.value == "BLOCKER" for f in findings)
        inputs = {
            metric: (None if metric in duplicates or blocked else row.value)
            for metric, row in by_metric.items()
        }
        values = calculate_annual_metrics(inputs)

        previous_revenue = await self._previous_annual_revenue(
            session, company_id=company_id, fiscal_year=fiscal_year - 1,
            policy=policy, as_known_at=as_known_at,
        )
        current_revenue = by_metric.get("FIN.REVENUE")
        growth_inputs_valid = (
            current_revenue is not None and previous_revenue is not None
            and current_revenue.unit == previous_revenue.unit
            and current_revenue.currency == previous_revenue.currency
            and not blocked and "FIN.REVENUE" not in duplicates
        )
        revenue_growth = calculate_growth(
            current_revenue.value if growth_inputs_valid else None,
            previous_revenue.value if growth_inputs_valid else None,
        )
        values.append(revenue_growth)

        run = FinancialMetricRun(
            company_id=company_id, fiscal_year=fiscal_year,
            resolution_policy=policy.value, as_known_at=as_known_at,
            engine_version=METRICS_VERSION,
            status="REVIEW_REQUIRED" if blocked or findings else "COMPLETED",
            created_at=datetime.now(UTC),
        )
        session.add(run)
        await session.flush()
        source_ids = {row.metric_id: row.id for row in selected}
        for metric_value in values:
            result = FinancialMetricResult(
                run_id=run.id, company_id=company_id, fiscal_year=fiscal_year,
                metric_id=metric_value.metric_id, value=metric_value.value,
                unit=metric_value.unit, status=metric_value.status.value,
                reason=metric_value.reason,
            )
            session.add(result)
            await session.flush()
            # Explicit input lineage; derived ratios depend on the exact facts used.
            for metric_id in self._input_metrics(metric_value.metric_id):
                fact_id = source_ids.get(metric_id)
                if fact_id is not None:
                    session.add(FinancialMetricLineage(
                        result_id=result.id, normalized_fact_id=fact_id,
                    ))
            if metric_value.metric_id == "FIN.REVENUE_GROWTH" and growth_inputs_valid:
                session.add(FinancialMetricLineage(
                    result_id=result.id, normalized_fact_id=previous_revenue.id,
                ))
        for finding in findings:
            session.add(FinancialQualityFinding(
                company_id=company_id, fiscal_year=fiscal_year, run_id=run.id,
                rule_id=finding.rule_id, severity=finding.severity.value,
                message=finding.message, metric_id=finding.metric_id,
                created_at=datetime.now(UTC),
            ))
        await session.flush()
        return {
            "run_id": str(run.id), "company_id": str(company_id),
            "fiscal_year": fiscal_year, "resolution_policy": policy.value,
            "as_known_at": as_known_at.isoformat() if as_known_at else None,
            "engine_version": METRICS_VERSION, "status": run.status,
            "findings": [f.__dict__ for f in findings],
            "metrics": [
                {"metric_id": value.metric_id,
                 "value": str(value.value) if value.value is not None else None,
                 "unit": value.unit, "status": value.status.value, "reason": value.reason}
                for value in values
            ],
        }

    async def _previous_annual_revenue(
        self, session: AsyncSession, *, company_id: UUID, fiscal_year: int,
        policy: ResolutionPolicy, as_known_at: date | None,
    ) -> NormalizedFinancialFact | None:
        stmt = select(NormalizedFinancialFact).where(
            NormalizedFinancialFact.company_id == company_id,
            NormalizedFinancialFact.fiscal_year == fiscal_year,
            NormalizedFinancialFact.period_kind == "ANNUAL",
            NormalizedFinancialFact.metric_id == "FIN.REVENUE",
        )
        rows = list((await session.scalars(stmt)).all())
        if policy == ResolutionPolicy.AS_KNOWN_AT:
            rows = [row for row in rows if row.filed_at is not None and row.filed_at <= as_known_at]
        if not rows:
            return None
        rows.sort(key=lambda item: (item.filed_at or date.min, item.available_at), reverse=True)
        # Multiple units/currencies are ambiguous; do not choose one silently.
        if len({(row.unit, row.currency) for row in rows}) > 1:
            return None
        return rows[0]

    @staticmethod
    def _input_metrics(metric_id: str) -> tuple[str, ...]:
        return {
            "FIN.GROSS_MARGIN": ("FIN.GROSS_PROFIT", "FIN.REVENUE"),
            "FIN.OPERATING_MARGIN": ("FIN.OPERATING_INCOME", "FIN.REVENUE"),
            "FIN.NET_MARGIN": ("FIN.NET_INCOME", "FIN.REVENUE"),
            "FIN.OCF_MARGIN": ("FIN.OCF", "FIN.REVENUE"),
            "FIN.FCF": ("FIN.OCF", "FIN.CAPEX"),
            "FIN.FCF_MARGIN": ("FIN.OCF", "FIN.CAPEX", "FIN.REVENUE"),
            "FIN.REVENUE_GROWTH": ("FIN.REVENUE",),
        }.get(metric_id, ())
