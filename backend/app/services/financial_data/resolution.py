from collections import defaultdict
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fact_resolution import ResolutionPolicy, eligible_by_policy
from app.models.financial_data import FinancialFact


class FinancialFactResolutionService:
    async def resolve(
        self,
        session: AsyncSession,
        *,
        company_id: UUID,
        policy: ResolutionPolicy = ResolutionPolicy.LATEST_RESTATED,
        as_known_at: date | None = None,
        metric_id: str | None = None,
    ) -> list[FinancialFact]:
        if policy == ResolutionPolicy.AS_KNOWN_AT and as_known_at is None:
            raise ValueError("AS_KNOWN_AT requires as_known_at")
        stmt = select(FinancialFact).where(FinancialFact.company_id == company_id)
        if metric_id:
            stmt = stmt.where(FinancialFact.metric_id == metric_id)
        rows = list((await session.scalars(stmt)).all())
        grouped: dict[tuple, list[FinancialFact]] = defaultdict(list)
        for fact in rows:
            if not eligible_by_policy(filed_at=fact.filed_at, policy=policy, cutoff=as_known_at):
                continue
            key = (
                fact.metric_id, fact.unit, fact.currency, fact.period_kind,
                fact.fiscal_year, fact.fiscal_period, fact.start_date, fact.end_date,
            )
            grouped[key].append(fact)
        resolved: list[FinancialFact] = []
        for candidates in grouped.values():
            candidates.sort(
                key=lambda item: (item.filed_at or date.min, item.retrieved_at),
                reverse=True,
            )
            resolved.append(candidates[0])
        return sorted(
            resolved,
            key=lambda item: (item.metric_id, item.end_date, item.unit),
        )
