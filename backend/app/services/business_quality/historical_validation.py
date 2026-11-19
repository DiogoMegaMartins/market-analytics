"""Point-in-time descriptive validation for approved Business Quality assessments.

This module measures score coverage/stability and cross-sectional rank consistency.
It does not test investment returns or establish predictive validity.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class HistoricalAssessment:
    company_key: str
    assessment_id: str
    as_of_date: date
    score: Decimal | None
    completeness_pct: Decimal
    confidence: str
    methodology_version: str
    approved: bool


@dataclass(frozen=True)
class CompanyHistory:
    company_key: str
    observations: int
    first_score: Decimal
    latest_score: Decimal
    absolute_change: Decimal
    mean_absolute_step_change: Decimal


@dataclass(frozen=True)
class PeriodCoverage:
    as_of_date: date
    eligible_companies: int
    excluded_unapproved: int
    excluded_incomplete: int
    methodology_versions: tuple[str, ...]


@dataclass(frozen=True)
class RankConsistency:
    earlier_date: date
    later_date: date
    common_companies: int
    spearman_rho: Decimal | None
    status: str


@dataclass(frozen=True)
class HistoricalValidationReport:
    company_histories: tuple[CompanyHistory, ...]
    period_coverage: tuple[PeriodCoverage, ...]
    rank_consistency: tuple[RankConsistency, ...]
    limitations: tuple[str, ...]


def _average_ranks(scores: dict[str, Decimal]) -> dict[str, Decimal]:
    ordered = sorted(scores.items(), key=lambda item: (item[1], item[0]))
    ranks: dict[str, Decimal] = {}
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        rank = (Decimal(i + 1) + Decimal(j)) / Decimal(2)
        for key, _ in ordered[i:j]:
            ranks[key] = rank
        i = j
    return ranks


def _spearman(left: dict[str, Decimal], right: dict[str, Decimal]) -> Decimal | None:
    if len(left) < 3:
        return None
    x, y = _average_ranks(left), _average_ranks(right)
    mean_x = sum(x.values()) / Decimal(len(x))
    mean_y = sum(y.values()) / Decimal(len(y))
    cov = sum((x[k] - mean_x) * (y[k] - mean_y) for k in x)
    var_x = sum((v - mean_x) ** 2 for v in x.values())
    var_y = sum((v - mean_y) ** 2 for v in y.values())
    if var_x == 0 or var_y == 0:
        return None
    # Decimal square root is deterministic and avoids floating-point drift.
    return (cov / (var_x * var_y).sqrt()).quantize(Decimal("0.0001"))


def validate_historical_assessments(
    assessments: Sequence[HistoricalAssessment],
    *,
    minimum_completeness_pct: Decimal = Decimal(80),
) -> HistoricalValidationReport:
    if not assessments:
        raise ValueError("At least one historical assessment is required")
    if not Decimal(0) <= minimum_completeness_pct <= Decimal(100):
        raise ValueError("Minimum completeness must be between 0 and 100")
    ids = [a.assessment_id for a in assessments]
    if any(not value.strip() for value in ids) or len(ids) != len(set(ids)):
        raise ValueError("Assessment IDs must be non-empty and unique")
    for a in assessments:
        if not a.company_key.strip() or not a.methodology_version.strip():
            raise ValueError("Company key and methodology version are required")
        if not Decimal(0) <= a.completeness_pct <= Decimal(100):
            raise ValueError("Completeness must be between 0 and 100")
        if a.score is not None and not Decimal(0) <= a.score <= Decimal(100):
            raise ValueError("Scores must be between 0 and 100")
        if a.confidence not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError("Invalid confidence")

    by_period: dict[date, list[HistoricalAssessment]] = {}
    by_company: dict[str, list[HistoricalAssessment]] = {}
    for item in assessments:
        by_period.setdefault(item.as_of_date, []).append(item)
        by_company.setdefault(item.company_key, []).append(item)

    period_scores: dict[date, dict[str, Decimal]] = {}
    coverage: list[PeriodCoverage] = []
    for period, rows in sorted(by_period.items()):
        eligible: dict[str, Decimal] = {}
        unapproved = incomplete = 0
        versions: set[str] = set()
        seen_companies: set[str] = set()
        for row in rows:
            if row.company_key in seen_companies:
                raise ValueError(f"Duplicate company assessment for period {period}: {row.company_key}")
            seen_companies.add(row.company_key)
            versions.add(row.methodology_version)
            if not row.approved:
                unapproved += 1
            elif row.score is None or row.completeness_pct < minimum_completeness_pct:
                incomplete += 1
            else:
                eligible[row.company_key] = row.score
        period_scores[period] = eligible
        coverage.append(PeriodCoverage(period, len(eligible), unapproved, incomplete, tuple(sorted(versions))))

    histories: list[CompanyHistory] = []
    for company, rows in sorted(by_company.items()):
        usable = sorted((r for r in rows if r.approved and r.score is not None
                         and r.completeness_pct >= minimum_completeness_pct), key=lambda r: r.as_of_date)
        if len(usable) < 2:
            continue
        if len({r.methodology_version for r in usable}) != 1:
            continue  # Never compare scores across methodology versions as if directly comparable.
        changes = [abs(usable[i].score - usable[i - 1].score) for i in range(1, len(usable))]
        histories.append(CompanyHistory(company, len(usable), usable[0].score, usable[-1].score,
                                        usable[-1].score - usable[0].score,
                                        (sum(changes) / Decimal(len(changes))).quantize(Decimal("0.01"))))

    periods = sorted(period_scores)
    rank_results: list[RankConsistency] = []
    for i, earlier in enumerate(periods):
        for later in periods[i + 1:]:
            common = sorted(set(period_scores[earlier]) & set(period_scores[later]))
            left = {k: period_scores[earlier][k] for k in common}
            right = {k: period_scores[later][k] for k in common}
            versions_left = {r.methodology_version for r in by_period[earlier] if r.company_key in common}
            versions_right = {r.methodology_version for r in by_period[later] if r.company_key in common}
            if versions_left != versions_right:
                rho, status = None, "METHODOLOGY_MISMATCH"
            else:
                rho = _spearman(left, right)
                status = "CALCULATED" if rho is not None else "INSUFFICIENT_CROSS_SECTION"
            rank_results.append(RankConsistency(earlier, later, len(common), rho, status))

    return HistoricalValidationReport(
        tuple(histories), tuple(coverage), tuple(rank_results),
        ("A análise é descritiva; não demonstra capacidade preditiva.",
         "Não mede retornos, alpha ou causalidade.",
         "Comparações temporais são omitidas quando a versão metodológica diverge.",
         "A amostra depende de avaliações aprovadas e do limiar de completude definido.",
         "Não corrige automaticamente enviesamento de sobrevivência ou look-ahead bias."),
    )
