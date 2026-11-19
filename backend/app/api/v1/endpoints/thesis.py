from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_company_access
from app.models.business_quality_evidence import BQEvidenceCandidate
from app.models.financial_data import FinancialMetricResult, FinancialMetricRun
from app.models.identity import Company
from app.models.thesis import InvestmentThesis, InvestmentThesisEvent, InvestmentThesisVersion
from app.models.thesis_alert import InvestmentThesisAlert, InvestmentThesisAlertEvent
from app.models.thesis_evidence import InvestmentThesisEvidenceLink
from app.platform.database.session import get_db_session
from app.services.thesis.evaluation import evaluate_thesis_assumptions, material_change

router = APIRouter(tags=["investment-thesis"], dependencies=[Depends(require_company_access)])


class AssumptionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assumption_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=1000)
    metric_id: str = Field(min_length=1, max_length=80)
    condition: str = Field(pattern="^(ABOVE|BELOW)$")
    threshold: Decimal
    unit: str = Field(min_length=1, max_length=30)

    @field_validator("threshold")
    @classmethod
    def finite_threshold(cls, value: Decimal) -> Decimal:
        if not value.is_finite():
            raise ValueError("threshold must be finite")
        return value


class ThesisVersionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=4000)
    rationale: str = Field(min_length=1, max_length=12000)
    assumptions: list[AssumptionInput] = Field(default_factory=list, max_length=50)
    risks: list[str] = Field(default_factory=list, max_length=50)
    evidence_references: list[str] = Field(default_factory=list, max_length=100)


class ThesisEvidenceLinkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assumption_id: str = Field(min_length=1, max_length=80)
    evidence_candidate_id: UUID | None = None
    metric_result_id: UUID | None = None
    relationship: str = Field(pattern="^(SUPPORTS|CONTRADICTS|QUALIFIES)$")
    rationale: str = Field(min_length=1, max_length=4000)

    @field_validator("evidence_candidate_id", "metric_result_id")
    @classmethod
    def at_least_one_target_value(cls, value):
        return value


class ThesisDecisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(pattern="^(KEEP|REVISE|INVALIDATE|ON_HOLD)$")
    comment: str | None = Field(default=None, max_length=4000)


class AlertStatusInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^(REVIEWED|RESOLVED)$")
    comment: str | None = Field(default=None, max_length=4000)


def _version_payload(payload: ThesisVersionInput) -> dict:
    assumptions = [item.model_dump(mode="json") for item in payload.assumptions]
    keys = [item["assumption_id"] for item in assumptions]
    if len(keys) != len(set(keys)):
        raise HTTPException(status_code=422, detail="assumption_id values must be unique")
    return {
        "title": payload.title,
        "summary": payload.summary,
        "rationale": payload.rationale,
        "assumptions": assumptions,
        "risks": payload.risks,
        "evidence_references": payload.evidence_references,
    }


async def _owned_thesis(thesis_id: UUID, request: Request, session: AsyncSession) -> InvestmentThesis:
    thesis = await session.get(InvestmentThesis, thesis_id)
    if thesis is None:
        raise HTTPException(status_code=404, detail="Thesis not found")
    user = request.state.authenticated_user
    if thesis.owner_user_id != user.id and request.state.company_role != "ADMIN":
        raise HTTPException(status_code=404, detail="Thesis not found")
    return thesis


async def _current_version(thesis: InvestmentThesis, session: AsyncSession) -> InvestmentThesisVersion:
    version = await session.scalar(select(InvestmentThesisVersion).where(
        InvestmentThesisVersion.thesis_id == thesis.id,
        InvestmentThesisVersion.version_number == thesis.current_version_number,
    ))
    if version is None:
        raise HTTPException(status_code=409, detail="Current thesis version is unavailable")
    return version


@router.post("/thesis/companies/{company_id}/theses", status_code=201)
async def create_thesis(
    company_id: UUID, payload: ThesisVersionInput, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    content = _version_payload(payload)
    now = datetime.now(UTC)
    thesis = InvestmentThesis(
        company_id=company_id, owner_user_id=request.state.authenticated_user.id,
        title=content["title"], status="ACTIVE", current_version_number=1,
        created_at=now, updated_at=now,
    )
    session.add(thesis)
    await session.flush()
    version = InvestmentThesisVersion(
        thesis_id=thesis.id, version_number=1, summary=content["summary"],
        rationale=content["rationale"], assumptions=content["assumptions"],
        risks=content["risks"], evidence_references=content["evidence_references"],
        author_user_id=request.state.authenticated_user.id, created_at=now,
    )
    session.add(version)
    await session.commit()
    return {"id": str(thesis.id), "company_id": str(company_id), "status": thesis.status,
            "current_version_number": 1, "version_id": str(version.id), "created_at": now.isoformat()}


@router.get("/thesis/companies/{company_id}/theses")
async def list_theses(
    company_id: UUID, request: Request, limit: int = Query(default=50, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    stmt = select(InvestmentThesis).where(InvestmentThesis.company_id == company_id)
    if request.state.company_role != "ADMIN":
        stmt = stmt.where(InvestmentThesis.owner_user_id == request.state.authenticated_user.id)
    records = list((await session.scalars(stmt.order_by(InvestmentThesis.updated_at.desc()).limit(limit))).all())
    return {"company_id": str(company_id), "theses": [
        {"id": str(item.id), "title": item.title, "status": item.status,
         "current_version_number": item.current_version_number,
         "updated_at": item.updated_at.isoformat()} for item in records
    ]}


@router.post("/thesis/{thesis_id}/versions", status_code=201)
async def create_thesis_version(
    thesis_id: UUID, payload: ThesisVersionInput, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    content = _version_payload(payload)
    now = datetime.now(UTC)
    next_number = thesis.current_version_number + 1
    version = InvestmentThesisVersion(
        thesis_id=thesis.id, version_number=next_number, summary=content["summary"],
        rationale=content["rationale"], assumptions=content["assumptions"],
        risks=content["risks"], evidence_references=content["evidence_references"],
        author_user_id=request.state.authenticated_user.id, created_at=now,
    )
    thesis.title = content["title"]
    thesis.current_version_number = next_number
    thesis.updated_at = now
    session.add(version)
    await session.commit()
    return {"thesis_id": str(thesis.id), "version_id": str(version.id),
            "version_number": next_number, "created_at": now.isoformat()}


@router.get("/thesis/{thesis_id}")
async def get_thesis(
    thesis_id: UUID, request: Request, session: AsyncSession = Depends(get_db_session),
) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    versions = list((await session.scalars(select(InvestmentThesisVersion).where(
        InvestmentThesisVersion.thesis_id == thesis.id
    ).order_by(InvestmentThesisVersion.version_number.desc()))).all())
    return {
        "id": str(thesis.id), "company_id": str(thesis.company_id), "title": thesis.title,
        "status": thesis.status, "current_version_number": thesis.current_version_number,
        "versions": [{
            "id": str(v.id), "version_number": v.version_number, "summary": v.summary,
            "rationale": v.rationale, "assumptions": v.assumptions, "risks": v.risks,
            "evidence_references": v.evidence_references,
            "author_user_id": str(v.author_user_id), "created_at": v.created_at.isoformat(),
        } for v in versions],
    }


@router.post("/thesis/{thesis_id}/evidence-links", status_code=201)
async def create_thesis_evidence_link(
    thesis_id: UUID, payload: ThesisEvidenceLinkInput, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    version = await _current_version(thesis, session)
    if (payload.evidence_candidate_id is None) == (payload.metric_result_id is None):
        raise HTTPException(status_code=422, detail="Provide exactly one evidence target")
    assumptions_by_id = {item.get("assumption_id"): item for item in version.assumptions if isinstance(item, dict)}
    if payload.assumption_id not in assumptions_by_id:
        raise HTTPException(status_code=422, detail="assumption_id is not present in the current thesis version")
    assumption = assumptions_by_id[payload.assumption_id]
    source_status = None
    if payload.evidence_candidate_id is not None:
        source = await session.get(BQEvidenceCandidate, payload.evidence_candidate_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Evidence candidate not found")
        if source.company_id != thesis.company_id:
            raise HTTPException(status_code=422, detail="Evidence candidate belongs to another company")
        source_status = source.status
        target_type = "DOCUMENT_EVIDENCE"
    else:
        source = await session.get(FinancialMetricResult, payload.metric_result_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Financial metric result not found")
        if source.company_id != thesis.company_id:
            raise HTTPException(status_code=422, detail="Financial metric belongs to another company")
        if source.metric_id != assumption.get("metric_id"):
            raise HTTPException(status_code=422, detail="Financial metric does not match the linked assumption metric_id")
        source_status = source.status
        target_type = "FINANCIAL_METRIC"
    now = datetime.now(UTC)
    link = InvestmentThesisEvidenceLink(
        thesis_id=thesis.id, version_id=version.id, assumption_id=payload.assumption_id,
        evidence_candidate_id=payload.evidence_candidate_id, metric_result_id=payload.metric_result_id,
        relationship=payload.relationship, rationale=payload.rationale,
        created_by=request.state.authenticated_user.id, created_at=now,
    )
    session.add(link)
    await session.commit()
    return {"id": str(link.id), "thesis_id": str(thesis.id), "version_id": str(version.id),
            "assumption_id": payload.assumption_id, "target_type": target_type,
            "target_id": str(payload.evidence_candidate_id or payload.metric_result_id),
            "source_status": source_status, "relationship": payload.relationship,
            "created_at": now.isoformat()}


@router.get("/thesis/{thesis_id}/intelligence")
async def get_thesis_intelligence(
    thesis_id: UUID, request: Request, session: AsyncSession = Depends(get_db_session),
) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    version = await _current_version(thesis, session)
    links = list((await session.scalars(select(InvestmentThesisEvidenceLink).where(
        InvestmentThesisEvidenceLink.thesis_id == thesis.id,
        InvestmentThesisEvidenceLink.version_id == version.id,
    ).order_by(InvestmentThesisEvidenceLink.created_at.asc()))).all())
    candidate_ids = [item.evidence_candidate_id for item in links if item.evidence_candidate_id]
    metric_ids = [item.metric_result_id for item in links if item.metric_result_id]
    candidates = {str(x.id): x for x in (await session.scalars(select(BQEvidenceCandidate).where(BQEvidenceCandidate.id.in_(candidate_ids)))).all()} if candidate_ids else {}
    metrics = {str(x.id): x for x in (await session.scalars(select(FinancialMetricResult).where(FinancialMetricResult.id.in_(metric_ids)))).all()} if metric_ids else {}
    by_assumption = {}
    for assumption in version.assumptions:
        aid = assumption.get("assumption_id") if isinstance(assumption, dict) else None
        if aid:
            by_assumption[aid] = {"assumption_id": aid, "description": assumption.get("description"),
                "supports": 0, "contradicts": 0, "qualifies": 0, "candidate_document_evidence": 0,
                "verified_document_evidence": 0, "rejected_or_superseded_document_evidence": 0,
                "calculated_metrics": 0, "other_metric_status": 0}
    for link in links:
        item = by_assumption.get(link.assumption_id)
        if item is None:
            continue
        item[{"SUPPORTS":"supports", "CONTRADICTS":"contradicts", "QUALIFIES":"qualifies"}[link.relationship]] += 1
        if link.evidence_candidate_id:
            status = candidates.get(str(link.evidence_candidate_id)).status if str(link.evidence_candidate_id) in candidates else "UNAVAILABLE"
            bucket = ("verified_document_evidence" if status == "VERIFIED" else
                      "candidate_document_evidence" if status == "CANDIDATE" else
                      "rejected_or_superseded_document_evidence")
            item[bucket] += 1
        elif link.metric_result_id:
            status = metrics.get(str(link.metric_result_id)).status if str(link.metric_result_id) in metrics else "UNAVAILABLE"
            item["calculated_metrics" if status == "CALCULATED" else "other_metric_status"] += 1
    return {"thesis_id": str(thesis.id), "version_id": str(version.id),
        "evidence_link_count": len(links), "assumptions": list(by_assumption.values()),
        "interpretation_policy": "Counts are descriptive only. CANDIDATE evidence is unreviewed; only VERIFIED documentary evidence and CALCULATED metrics are identified as such. No automatic score or thesis status change is performed."}


@router.get("/thesis/{thesis_id}/evidence-links")
async def list_thesis_evidence_links(
    thesis_id: UUID, request: Request, session: AsyncSession = Depends(get_db_session),
) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    rows = list((await session.scalars(select(InvestmentThesisEvidenceLink).where(
        InvestmentThesisEvidenceLink.thesis_id == thesis.id
    ).order_by(InvestmentThesisEvidenceLink.created_at.asc()))).all())
    return {"thesis_id": str(thesis.id), "evidence_links": [{
        "id": str(row.id), "version_id": str(row.version_id), "assumption_id": row.assumption_id,
        "evidence_candidate_id": str(row.evidence_candidate_id) if row.evidence_candidate_id else None,
        "metric_result_id": str(row.metric_result_id) if row.metric_result_id else None,
        "relationship": row.relationship, "rationale": row.rationale,
        "created_at": row.created_at.isoformat(),
    } for row in rows]}


@router.post("/thesis/{thesis_id}/evaluate")
async def evaluate_thesis(
    thesis_id: UUID, request: Request, fiscal_year: int = Query(..., ge=1900, le=2200),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    version = await _current_version(thesis, session)
    run = await session.scalar(select(FinancialMetricRun).where(
        FinancialMetricRun.company_id == thesis.company_id,
        FinancialMetricRun.fiscal_year == fiscal_year,
    ).order_by(FinancialMetricRun.created_at.desc(), FinancialMetricRun.id.desc()).limit(1))
    metrics = []
    if run is not None:
        rows = list((await session.scalars(select(FinancialMetricResult).where(
            FinancialMetricResult.run_id == run.id
        ))).all())
        metrics = [{"metric_id": row.metric_id,
                    "value": str(row.value) if row.value is not None else None,
                    "unit": row.unit, "status": row.status} for row in rows]
    evaluation = evaluate_thesis_assumptions(
        assumptions=version.assumptions, metrics=metrics, fiscal_year=fiscal_year,
    )
    evaluation["metric_run_id"] = str(run.id) if run else None
    evaluation["metric_engine_version"] = run.engine_version if run else None
    now = datetime.now(UTC)
    event = InvestmentThesisEvent(
        thesis_id=thesis.id, version_id=version.id, event_type="DETERMINISTIC_EVALUATION",
        decision=evaluation["overall_status"], payload=evaluation,
        actor_user_id=request.state.authenticated_user.id, created_at=now,
    )
    session.add(event)
    await session.commit()
    return {"event_id": str(event.id), **evaluation}


MATERIAL_CHANGE_PERCENT = Decimal(20)


@router.post("/thesis/{thesis_id}/monitor")
async def monitor_thesis(
    thesis_id: UUID, request: Request, fiscal_year: int | None = Query(default=None, ge=1900, le=2200),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Evaluate the latest persisted metric run and idempotently persist review alerts."""
    thesis = await _owned_thesis(thesis_id, request, session)
    version = await _current_version(thesis, session)
    stmt = select(FinancialMetricRun).where(FinancialMetricRun.company_id == thesis.company_id)
    if fiscal_year is not None:
        stmt = stmt.where(FinancialMetricRun.fiscal_year == fiscal_year)
    run = await session.scalar(stmt.order_by(FinancialMetricRun.fiscal_year.desc(), FinancialMetricRun.created_at.desc(), FinancialMetricRun.id.desc()).limit(1))
    if run is None:
        return {"thesis_id": str(thesis.id), "created_alerts": 0, "alerts": [], "reason": "No persisted metric run is available."}
    rows = list((await session.scalars(select(FinancialMetricResult).where(FinancialMetricResult.run_id == run.id))).all())
    metrics = [{"metric_id": row.metric_id, "value": str(row.value) if row.value is not None else None,
                "unit": row.unit, "status": row.status} for row in rows]
    evaluation = evaluate_thesis_assumptions(assumptions=version.assumptions, metrics=metrics, fiscal_year=run.fiscal_year)
    previous = await session.scalar(select(FinancialMetricRun).where(
        FinancialMetricRun.company_id == thesis.company_id,
        FinancialMetricRun.fiscal_year < run.fiscal_year,
    ).order_by(FinancialMetricRun.fiscal_year.desc(), FinancialMetricRun.created_at.desc(), FinancialMetricRun.id.desc()).limit(1))
    previous_by_metric = {}
    if previous:
        previous_rows = list((await session.scalars(select(FinancialMetricResult).where(FinancialMetricResult.run_id == previous.id))).all())
        previous_by_metric = {r.metric_id: r for r in previous_rows if r.status == "CALCULATED" and r.value is not None}
    current_by_metric = {r.metric_id: r for r in rows if r.status == "CALCULATED" and r.value is not None}
    created = []
    now = datetime.now(UTC)
    for item in evaluation["assumption_evaluations"]:
        detected = ([ ("THRESHOLD_BREACH", {"evaluation": item}) ]
                    if item["status"] == "BREACH_CANDIDATE" else [])
        current = current_by_metric.get(item["metric_id"])
        prior = previous_by_metric.get(item["metric_id"])
        if current is not None and prior is not None and str(current.unit) == str(prior.unit):
            change = material_change(prior.value, current.value, threshold_percent=MATERIAL_CHANGE_PERCENT)
            if change:
                detected.append(("MATERIAL_CHANGE", {**change, "unit": str(current.unit),
                    "previous_metric_run_id": str(previous.id)}))
        for alert_type, details in detected:
            existing = await session.scalar(select(InvestmentThesisAlert).where(
                InvestmentThesisAlert.thesis_id == thesis.id, InvestmentThesisAlert.version_id == version.id,
                InvestmentThesisAlert.assumption_id == item["assumption_id"], InvestmentThesisAlert.metric_run_id == run.id,
                InvestmentThesisAlert.alert_type == alert_type))
            if existing:
                continue
            alert = InvestmentThesisAlert(thesis_id=thesis.id, version_id=version.id,
                assumption_id=item["assumption_id"], metric_run_id=run.id, alert_type=alert_type,
                status="PENDING", summary=("Potential quantitative assumption breach" if alert_type == "THRESHOLD_BREACH" else "Material quantitative metric change"),
                details=details, created_at=now, updated_at=now)
            session.add(alert)
            await session.flush()
            session.add(InvestmentThesisAlertEvent(alert_id=alert.id, from_status=None, to_status="PENDING",
                actor_user_id=request.state.authenticated_user.id, comment="Detected deterministically; analyst review required.", created_at=now))
            created.append(alert)
    event = InvestmentThesisEvent(thesis_id=thesis.id, version_id=version.id,
        event_type="DETERMINISTIC_MONITORING", decision="ALERTS_CREATED" if created else "NO_NEW_ALERTS",
        payload={"metric_run_id": str(run.id), "fiscal_year": run.fiscal_year,
            "created_alert_ids": [str(a.id) for a in created], "automatic_invalidation": False,
            "materiality_percent": str(MATERIAL_CHANGE_PERCENT)},
        actor_user_id=request.state.authenticated_user.id, created_at=now)
    session.add(event)
    await session.commit()
    return {"thesis_id": str(thesis.id), "metric_run_id": str(run.id), "fiscal_year": run.fiscal_year,
        "created_alerts": len(created), "alerts": [{"id": str(a.id), "assumption_id": a.assumption_id,
            "alert_type": a.alert_type, "status": a.status, "summary": a.summary} for a in created],
        "automatic_invalidation": False, "materiality_percent": str(MATERIAL_CHANGE_PERCENT)}


@router.get("/thesis/{thesis_id}/alerts")
async def list_thesis_alerts(thesis_id: UUID, request: Request, session: AsyncSession = Depends(get_db_session)) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    alerts = list((await session.scalars(select(InvestmentThesisAlert).where(
        InvestmentThesisAlert.thesis_id == thesis.id).order_by(InvestmentThesisAlert.created_at.desc()))).all())
    run_ids = {alert.metric_run_id for alert in alerts}
    metric_runs = {
        run.id: run for run in (await session.scalars(
            select(FinancialMetricRun).where(FinancialMetricRun.id.in_(run_ids))
        )).all()
    } if run_ids else {}
    result = []
    for alert in alerts:
        history = list((await session.scalars(select(InvestmentThesisAlertEvent).where(
            InvestmentThesisAlertEvent.alert_id == alert.id).order_by(InvestmentThesisAlertEvent.created_at))).all())
        metric_run = metric_runs.get(alert.metric_run_id)
        result.append({"id": str(alert.id), "version_id": str(alert.version_id), "assumption_id": alert.assumption_id,
            "metric_run_id": str(alert.metric_run_id), "metric_run": ({
                "id": str(metric_run.id), "fiscal_year": metric_run.fiscal_year,
                "created_at": metric_run.created_at.isoformat(), "engine_version": metric_run.engine_version,
                "resolution_policy": metric_run.resolution_policy, "as_known_at": (
                    metric_run.as_known_at.isoformat() if metric_run.as_known_at else None
                ), "status": metric_run.status,
            } if metric_run else None),
            "alert_type": alert.alert_type, "status": alert.status,
            "summary": alert.summary, "details": alert.details, "created_at": alert.created_at.isoformat(),
            "updated_at": alert.updated_at.isoformat(), "history": [{"from_status": e.from_status,
                "to_status": e.to_status, "actor_user_id": str(e.actor_user_id), "comment": e.comment,
                "created_at": e.created_at.isoformat()} for e in history]})
    return {"thesis_id": str(thesis.id), "alerts": result}


@router.patch("/thesis/{thesis_id}/alerts/{alert_id}")
async def update_thesis_alert(thesis_id: UUID, alert_id: UUID, payload: AlertStatusInput, request: Request,
                              session: AsyncSession = Depends(get_db_session)) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    if request.state.company_role not in {"ANALYST", "ADMIN"}:
        raise HTTPException(status_code=403, detail="Insufficient company role")
    alert = await session.scalar(select(InvestmentThesisAlert).where(
        InvestmentThesisAlert.id == alert_id, InvestmentThesisAlert.thesis_id == thesis.id))
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    allowed = {"PENDING": {"REVIEWED", "RESOLVED"}, "REVIEWED": {"RESOLVED"}, "RESOLVED": set()}
    if payload.status not in allowed[alert.status]:
        raise HTTPException(status_code=409, detail=f"Invalid alert transition: {alert.status} to {payload.status}")
    now = datetime.now(UTC)
    previous = alert.status
    alert.status = payload.status
    alert.updated_at = now
    session.add(InvestmentThesisAlertEvent(alert_id=alert.id, from_status=previous, to_status=payload.status,
        actor_user_id=request.state.authenticated_user.id, comment=payload.comment, created_at=now))
    await session.commit()
    return {"id": str(alert.id), "status": alert.status, "updated_at": now.isoformat(), "automatic_thesis_change": False}


@router.post("/thesis/{thesis_id}/decisions", status_code=201)
async def record_thesis_decision(
    thesis_id: UUID, payload: ThesisDecisionInput, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    version = await _current_version(thesis, session)
    now = datetime.now(UTC)
    status_by_decision = {"KEEP": "ACTIVE", "REVISE": "ACTIVE",
                          "INVALIDATE": "INVALIDATED", "ON_HOLD": "ON_HOLD"}
    thesis.status = status_by_decision[payload.decision]
    thesis.updated_at = now
    event = InvestmentThesisEvent(
        thesis_id=thesis.id, version_id=version.id, event_type="ANALYST_DECISION",
        decision=payload.decision,
        payload={"comment": payload.comment, "resulting_status": thesis.status,
                 "automatic": False, "requires_new_version_for_revision": payload.decision == "REVISE"},
        actor_user_id=request.state.authenticated_user.id, created_at=now,
    )
    session.add(event)
    await session.commit()
    return {"event_id": str(event.id), "thesis_id": str(thesis.id),
            "decision": payload.decision, "status": thesis.status,
            "created_at": now.isoformat()}


@router.get("/thesis/{thesis_id}/events")
async def list_thesis_events(
    thesis_id: UUID, request: Request, session: AsyncSession = Depends(get_db_session),
) -> dict:
    thesis = await _owned_thesis(thesis_id, request, session)
    events = list((await session.scalars(select(InvestmentThesisEvent).where(
        InvestmentThesisEvent.thesis_id == thesis.id
    ).order_by(InvestmentThesisEvent.created_at, InvestmentThesisEvent.id))).all())
    return {"thesis_id": str(thesis.id), "events": [
        {"id": str(e.id), "version_id": str(e.version_id), "event_type": e.event_type,
         "decision": e.decision, "payload": e.payload, "actor_user_id": str(e.actor_user_id),
         "created_at": e.created_at.isoformat()} for e in events
    ]}
