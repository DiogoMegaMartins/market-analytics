from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from hashlib import sha256
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.financial_data import FinancialFactLineage, NormalizedFinancialFact

DERIVATION_VERSION = "quarter-derivation-v1.0"


@dataclass(frozen=True)
class QuarterValue:
    metric_id: str
    fiscal_year: int
    fiscal_period: str
    value: Decimal
    unit: str
    currency: str | None
    start_date: date | None
    end_date: date
    minuend: NormalizedFinancialFact
    subtrahend: NormalizedFinancialFact


def derive_quarter(
    *, metric_id: str, fiscal_year: int, fiscal_period: str,
    minuend: NormalizedFinancialFact, subtrahend: NormalizedFinancialFact,
) -> QuarterValue:
    if fiscal_period not in {"Q2", "Q3", "Q4"}:
        raise ValueError("Only Q2, Q3 and Q4 are derived by this policy")
    for field in ("company_id", "metric_id", "fiscal_year", "unit", "currency"):
        if getattr(minuend, field) != getattr(subtrahend, field):
            raise ValueError(f"Quarter derivation input mismatch: {field}")
    if minuend.metric_id != metric_id or minuend.fiscal_year != fiscal_year:
        raise ValueError("Quarter derivation inputs do not match requested metric and fiscal year")
    if minuend.end_date <= subtrahend.end_date:
        raise ValueError("Quarter derivation periods are not chronologically ordered")
    if minuend.value is None or subtrahend.value is None:
        raise ValueError("Quarter derivation inputs must have values")
    return QuarterValue(
        metric_id=metric_id, fiscal_year=fiscal_year, fiscal_period=fiscal_period,
        value=minuend.value - subtrahend.value, unit=minuend.unit,
        currency=minuend.currency,
        start_date=subtrahend.end_date.fromordinal(subtrahend.end_date.toordinal() + 1),
        end_date=minuend.end_date, minuend=minuend, subtrahend=subtrahend,
    )


class FinancialQuarterDerivationService:
    async def derive_company_year(
        self, session: AsyncSession, *, company_id: UUID, fiscal_year: int,
        as_known_at: date | None = None,
    ) -> dict:
        rows = list((await session.scalars(select(NormalizedFinancialFact).where(
            NormalizedFinancialFact.company_id == company_id,
            NormalizedFinancialFact.fiscal_year == fiscal_year,
            NormalizedFinancialFact.period_kind.in_(["ANNUAL", "YTD", "QUARTER"]),
        ))).all())
        if as_known_at is not None:
            # Filing date is date-granular in this data model; unknown dates are excluded.
            rows = [row for row in rows if row.filed_at is not None and row.filed_at <= as_known_at]
        grouped: dict[tuple, list[NormalizedFinancialFact]] = {}
        for row in rows:
            grouped.setdefault((row.metric_id, row.unit, row.currency), []).append(row)
        created = 0
        skipped: list[str] = []
        for (metric_id, unit, currency), candidates in grouped.items():
            def latest(period_kind: str, fiscal_period: str, candidates_for_group=candidates):
                matches = [r for r in candidates_for_group if r.period_kind == period_kind and r.fiscal_period == fiscal_period]
                matches.sort(key=lambda r: (r.filed_at or date.min, r.available_at), reverse=True)
                return matches[0] if matches else None

            q1 = latest("QUARTER", "Q1") or latest("YTD", "Q1")
            q2_ytd = latest("YTD", "Q2")
            q3_ytd = latest("YTD", "Q3")
            annual = latest("ANNUAL", "FY") or latest("ANNUAL", "FY ")
            specs = []
            if q1 and q2_ytd:
                specs.append(("Q2", q2_ytd, q1))
            if q2_ytd and q3_ytd:
                specs.append(("Q3", q3_ytd, q2_ytd))
            if q3_ytd and annual:
                specs.append(("Q4", annual, q3_ytd))
            for period, minuend, subtrahend in specs:
                try:
                    result = derive_quarter(metric_id=metric_id, fiscal_year=fiscal_year,
                                            fiscal_period=period, minuend=minuend,
                                            subtrahend=subtrahend)
                except ValueError as exc:
                    skipped.append(f"{metric_id}:{period}:{exc}")
                    continue
                key_raw = "|".join((DERIVATION_VERSION, str(company_id), metric_id,
                                    str(fiscal_year), period, str(minuend.id), str(subtrahend.id)))
                normalized_key = sha256(key_raw.encode()).hexdigest()
                exists = await session.scalar(select(NormalizedFinancialFact.id).where(
                    NormalizedFinancialFact.normalized_key == normalized_key))
                if exists:
                    continue
                row = NormalizedFinancialFact(
                    company_id=company_id, source_fact_id=minuend.source_fact_id,
                    metric_id=metric_id, value=result.value, unit=unit, currency=currency,
                    period_kind="QUARTER", fiscal_year=fiscal_year, fiscal_period=period,
                    start_date=result.start_date, end_date=result.end_date,
                    origin="DERIVED", derivation_version=DERIVATION_VERSION,
                    normalized_key=normalized_key,
                    filed_at=max((d for d in (minuend.filed_at, subtrahend.filed_at) if d), default=None),
                    available_at=max(minuend.available_at, subtrahend.available_at),
                )
                session.add(row)
                await session.flush()
                for source, role in ((minuend, "MINUEND"), (subtrahend, "SUBTRAHEND")):
                    session.add(FinancialFactLineage(
                        normalized_fact_id=row.id, source_fact_id=source.source_fact_id, role=role,
                    ))
                created += 1
        await session.flush()
        return {"company_id": str(company_id), "fiscal_year": fiscal_year,
                "as_known_at": as_known_at.isoformat() if as_known_at else None,
                "derivation_version": DERIVATION_VERSION, "created_quarters": created,
                "skipped": skipped}
