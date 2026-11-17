import base64 as _base64
import hashlib as _hashlib
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import require_company_access
from app.core.config import get_settings
from app.models.business_quality import BusinessQualityAssessment
from app.models.business_quality_evidence import (
    BQDocumentSection,
    BQEvidenceCandidate,
    BQSourceDocument,
)
from app.models.business_quality_evidence_audit import (
    BQAssessmentEvidenceLink,
    BQEvidenceReviewEvent,
)
from app.models.business_quality_review import BusinessQualityReviewEvent
from app.models.identity import Company
from app.platform.database.session import get_db_session
from app.services.business_quality.engine import Observation, assess_business_quality
from app.services.business_quality.evidence_extraction import (
    EXTRACTION_VERSION,
    criterion_catalog,
    detect_potential_conflicts,
    extract_evidence_candidates,
)
from app.services.business_quality.evidence_review import (
    build_review_event_hash,
    validate_evidence_transition,
)
from app.services.business_quality.point_in_time import (
    EvidenceRecord,
    evaluate_point_in_time_evidence,
)
from app.services.business_quality.review import next_review_status
from app.services.research.brief import ResearchDocument, ResearchSection, build_research_brief
from app.services.research.copilot import answer_research_question
from app.services.research.openai_provider import OpenAIResponsesModel, ResearchProviderError
from app.services.research.what_changed import build_what_changed

router = APIRouter(tags=["business-quality"], dependencies=[Depends(require_company_access)])


class ObservationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    score: Decimal = Field(ge=0, le=100)
    evidence_reference: str = Field(min_length=1, max_length=1000)
    rationale: str = Field(min_length=1, max_length=4000)
    confidence: str = "MEDIUM"


class ReviewActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(pattern="^(SUBMIT|REVIEW|APPROVE|REJECT)$")
    comment: str | None = Field(default=None, max_length=4000)


class AssessmentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    observations: dict[str, ObservationInput]
    notes: str | None = Field(default=None, max_length=4000)


@router.post("/business-quality/companies/{company_id}/assessments", status_code=201)
async def create_business_quality_assessment(
    company_id: UUID, payload: AssessmentInput, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    observations = {key: Observation(score=item.score, evidence_reference=item.evidence_reference,
                                      rationale=item.rationale, confidence=item.confidence)
                    for key, item in payload.observations.items()}
    try:
        result = assess_business_quality(observations)
    except (ValueError, ArithmeticError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result_json = {
        "score": str(result.score) if result.score is not None else None,
        "classification": result.classification, "status": result.status,
        "completeness_pct": str(result.completeness_pct),
        "analysis_confidence": result.analysis_confidence,
        "dimensions": [{"dimension": d.dimension, "score": str(d.score) if d.score is not None else None,
                        "status": d.status, "completeness_pct": str(d.completeness_pct),
                        "confidence": d.confidence, "missing_required": list(d.missing_required)}
                       for d in result.dimensions],
    }
    observation_json = {k: {"score": str(v.score), "evidence_reference": v.evidence_reference,
                            "rationale": v.rationale, "confidence": v.confidence}
                        for k, v in observations.items()}
    record = BusinessQualityAssessment(
        company_id=company_id, engine_version=result.engine_version, rubric_version=result.engine_version,
        status=result.status, overall_score=result.score, classification=result.classification,
        completeness_pct=result.completeness_pct, analysis_confidence=result.analysis_confidence,
        observations=observation_json, results=result_json, analyst_id=str(request.state.authenticated_user.id),
        notes=payload.notes, created_at=datetime.now(UTC),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return {"id": str(record.id), "company_id": str(company_id), "created_at": record.created_at.isoformat(), "review_status": "DRAFT", **result_json}


@router.get("/business-quality/companies/{company_id}/assessments")
async def list_business_quality_assessments(
    company_id: UUID, limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    records = list((await session.scalars(select(BusinessQualityAssessment).where(
        BusinessQualityAssessment.company_id == company_id
    ).order_by(BusinessQualityAssessment.created_at.desc()).limit(limit))).all())
    return {"company_id": str(company_id), "assessments": [
        {"id": str(r.id), "created_at": r.created_at.isoformat(), "engine_version": r.engine_version,
         "status": r.status, "score": str(r.overall_score) if r.overall_score is not None else None,
         "classification": r.classification, "completeness_pct": str(r.completeness_pct),
         "analysis_confidence": r.analysis_confidence} for r in records
    ]}


@router.get("/business-quality/assessments/{assessment_id}")
async def get_business_quality_assessment(
    assessment_id: UUID, session: AsyncSession = Depends(get_db_session),
) -> dict:
    record = await session.get(BusinessQualityAssessment, assessment_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return {"id": str(record.id), "company_id": str(record.company_id),
            "created_at": record.created_at.isoformat(), "engine_version": record.engine_version,
            "rubric_version": record.rubric_version, "analyst_id": record.analyst_id,
            "notes": record.notes, "observations": record.observations, **record.results}


@router.post("/business-quality/assessments/{assessment_id}/review-events", status_code=201)
async def add_business_quality_review_event(
    assessment_id: UUID, payload: ReviewActionInput, request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    # Lock assessment row so concurrent reviewers cannot apply transitions from the same state.
    record = await session.scalar(select(BusinessQualityAssessment).where(
        BusinessQualityAssessment.id == assessment_id
    ).with_for_update())
    if record is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    role = request.state.company_role
    if payload.action == "SUBMIT" and role not in {"ANALYST", "ADMIN"}:
        raise HTTPException(status_code=403, detail="ANALYST role required to submit")
    if payload.action != "SUBMIT" and role not in {"REVIEWER", "ADMIN"}:
        raise HTTPException(status_code=403, detail="REVIEWER role required for review decisions")
    latest = await session.scalar(select(BusinessQualityReviewEvent).where(
        BusinessQualityReviewEvent.assessment_id == assessment_id
    ).order_by(BusinessQualityReviewEvent.created_at.desc(), BusinessQualityReviewEvent.id.desc()).limit(1))
    current = latest.to_status if latest else "DRAFT"
    try:
        target = next_review_status(current, payload.action, analyst_id=record.analyst_id,
                                    actor_id=str(request.state.authenticated_user.id), comment=payload.comment)
    except ValueError as exc:
        status_code = 409 if "not allowed" in str(exc) else 422
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    event = BusinessQualityReviewEvent(assessment_id=assessment_id, from_status=current, to_status=target,
        action=payload.action, actor_id=str(request.state.authenticated_user.id), comment=payload.comment, created_at=datetime.now(UTC))
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return {"event_id": str(event.id), "assessment_id": str(assessment_id),
            "from_status": current, "review_status": target, "action": payload.action,
            "actor_id": str(request.state.authenticated_user.id), "created_at": event.created_at.isoformat()}


@router.get("/business-quality/assessments/{assessment_id}/review-events")
async def list_business_quality_review_events(
    assessment_id: UUID, session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(BusinessQualityAssessment, assessment_id) is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    events = list((await session.scalars(select(BusinessQualityReviewEvent).where(
        BusinessQualityReviewEvent.assessment_id == assessment_id
    ).order_by(BusinessQualityReviewEvent.created_at, BusinessQualityReviewEvent.id))).all())
    status = events[-1].to_status if events else "DRAFT"
    return {"assessment_id": str(assessment_id), "review_status": status, "events": [
        {"id": str(e.id), "from_status": e.from_status, "to_status": e.to_status,
         "action": e.action, "actor_id": e.actor_id, "comment": e.comment,
         "created_at": e.created_at.isoformat()} for e in events]}

# Persistent document/evidence endpoints. Raw source bytes are retained for reproducibility.
class SourceDocumentInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    accession_number: str = Field(min_length=1, max_length=32)
    form_type: str = Field(pattern="^(10-K|10-Q|20-F|6-K)$")
    filed_at: datetime
    published_at: datetime | None = None
    source_url: str = Field(min_length=1, max_length=2000)
    content_type: str = Field(min_length=1, max_length=120)
    original_content_base64: str = Field(min_length=1)
    extraction_version: str = Field(default="sec-html-v1", max_length=40)

class DocumentSectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_key: str = Field(min_length=1, max_length=80)
    heading: str = Field(min_length=1, max_length=500)
    sequence_number: int = Field(ge=0)
    text_content: str = Field(min_length=1)
    extraction_method: str = Field(default="HEURISTIC", max_length=40)

class EvidenceCandidateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    section_id: UUID | None = None
    criterion_key: str = Field(min_length=1, max_length=100)
    passage: str = Field(min_length=1, max_length=12000)
    rationale: str = Field(min_length=1, max_length=4000)
    source_locator: str = Field(min_length=1, max_length=500)

class EvidenceReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str = Field(pattern="^(VERIFIED|REJECTED|SUPERSEDED)$")
    review_comment: str = Field(min_length=1, max_length=4000)

@router.post("/business-quality/companies/{company_id}/source-documents", status_code=201)
async def persist_bq_source_document(company_id: UUID, payload: SourceDocumentInput,
                                     session: AsyncSession = Depends(get_db_session)) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    try:
        content = _base64.b64decode(payload.original_content_base64, validate=True)
    except (ValueError, _base64.binascii.Error) as exc:
        raise HTTPException(status_code=422, detail="Invalid base64 document content") from exc
    if not content or len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Document must be between 1 byte and 20 MB")
    if not payload.source_url.startswith("https://www.sec.gov/"):
        raise HTTPException(status_code=422, detail="Only official SEC HTTPS source URLs are accepted")
    digest = _hashlib.sha256(content).hexdigest()
    record = BQSourceDocument(company_id=company_id, accession_number=payload.accession_number,
        form_type=payload.form_type, filed_at=payload.filed_at, published_at=payload.published_at,
        source_url=payload.source_url, content_type=payload.content_type, document_hash=digest,
        original_content=content, extraction_version=payload.extraction_version, created_at=datetime.now(UTC))
    session.add(record)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    await session.refresh(record)
    return {"id": str(record.id), "company_id": str(company_id), "accession_number": record.accession_number,
            "document_hash": digest, "size_bytes": len(content), "immutable": True}

@router.post("/business-quality/source-documents/{document_id}/sections", status_code=201)
async def persist_bq_document_section(document_id: UUID, payload: DocumentSectionInput,
                                      session: AsyncSession = Depends(get_db_session)) -> dict:
    document = await session.get(BQSourceDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Source document not found")
    digest = _hashlib.sha256(payload.text_content.encode("utf-8")).hexdigest()
    section = BQDocumentSection(document_id=document_id, section_key=payload.section_key, heading=payload.heading,
        sequence_number=payload.sequence_number, text_content=payload.text_content, content_hash=digest,
        extraction_method=payload.extraction_method, created_at=datetime.now(UTC))
    session.add(section)
    await session.commit()
    await session.refresh(section)
    return {"id": str(section.id), "document_id": str(document_id), "section_key": section.section_key,
            "content_hash": digest}

@router.post("/business-quality/companies/{company_id}/evidence-candidates", status_code=201)
async def create_bq_evidence_candidate(company_id: UUID, payload: EvidenceCandidateInput, request: Request,
                                       session: AsyncSession = Depends(get_db_session)) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    # Document identity is supplied via the section, or must be provided by a later API revision.
    if payload.section_id is None:
        raise HTTPException(status_code=422, detail="section_id is required for traceable evidence")
    section = await session.get(BQDocumentSection, payload.section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Document section not found")
    source_document = await session.get(BQSourceDocument, section.document_id)
    if source_document is None or source_document.company_id != company_id:
        raise HTTPException(status_code=422, detail="Section does not belong to the requested company")
    digest = _hashlib.sha256(payload.passage.encode("utf-8")).hexdigest()
    item = BQEvidenceCandidate(company_id=company_id, document_id=source_document.id, section_id=section.id,
        criterion_key=payload.criterion_key, passage=payload.passage, rationale=payload.rationale,
        status="CANDIDATE", source_locator=payload.source_locator, evidence_hash=digest,
        created_by=str(request.state.authenticated_user.id), created_at=datetime.now(UTC))
    session.add(item)
    await session.flush()
    event_time = datetime.now(UTC)
    initial_hash = build_review_event_hash(candidate_id=str(item.id), from_status=None, to_status="CANDIDATE",
        actor_id=str(request.state.authenticated_user.id), comment="Evidence candidate created", previous_event_hash=None, created_at=event_time)
    session.add(BQEvidenceReviewEvent(candidate_id=item.id, from_status=None, to_status="CANDIDATE",
        actor_id=str(request.state.authenticated_user.id), comment="Evidence candidate created", previous_event_hash=None,
        event_hash=initial_hash, created_at=event_time))
    await session.commit()
    await session.refresh(item)
    return {"id": str(item.id), "status": item.status, "evidence_hash": digest, "document_id": str(item.document_id)}

@router.post("/business-quality/evidence-candidates/{candidate_id}/review")
async def review_bq_evidence_candidate(candidate_id: UUID, payload: EvidenceReviewInput, request: Request,
                                       session: AsyncSession = Depends(get_db_session)) -> dict:
    item = await session.scalar(select(BQEvidenceCandidate).where(
        BQEvidenceCandidate.id == candidate_id).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence candidate not found")
    try:
        validate_evidence_transition(item.status, payload.status, creator_id=item.created_by,
                                     actor_id=str(request.state.authenticated_user.id), comment=payload.review_comment)
    except ValueError as exc:
        raise HTTPException(status_code=409 if "not allowed" in str(exc) else 422, detail=str(exc)) from exc
    previous = await session.scalar(select(BQEvidenceReviewEvent).where(
        BQEvidenceReviewEvent.candidate_id == candidate_id).order_by(
        BQEvidenceReviewEvent.created_at.desc(), BQEvidenceReviewEvent.id.desc()).limit(1))
    event_time = datetime.now(UTC)
    previous_hash = previous.event_hash if previous else None
    event_hash = build_review_event_hash(candidate_id=str(candidate_id), from_status=item.status,
        to_status=payload.status, actor_id=str(request.state.authenticated_user.id), comment=payload.review_comment,
        previous_event_hash=previous_hash, created_at=event_time)
    session.add(BQEvidenceReviewEvent(candidate_id=candidate_id, from_status=item.status,
        to_status=payload.status, actor_id=str(request.state.authenticated_user.id), comment=payload.review_comment,
        previous_event_hash=previous_hash, event_hash=event_hash, created_at=event_time))
    item.status = payload.status
    item.reviewed_by = str(request.state.authenticated_user.id)
    item.review_comment = payload.review_comment
    await session.commit()
    return {"id": str(item.id), "status": item.status, "reviewed_by": item.reviewed_by,
            "event_hash": event_hash}


@router.get("/business-quality/evidence-candidates/{candidate_id}/review-events")
async def list_bq_evidence_review_events(candidate_id: UUID,
                                         session: AsyncSession = Depends(get_db_session)) -> dict:
    if await session.get(BQEvidenceCandidate, candidate_id) is None:
        raise HTTPException(status_code=404, detail="Evidence candidate not found")
    events = list((await session.scalars(select(BQEvidenceReviewEvent).where(
        BQEvidenceReviewEvent.candidate_id == candidate_id).order_by(
        BQEvidenceReviewEvent.created_at, BQEvidenceReviewEvent.id))).all())
    return {"candidate_id": str(candidate_id), "events": [
        {"id": str(e.id), "from_status": e.from_status, "to_status": e.to_status,
         "actor_id": e.actor_id, "comment": e.comment, "previous_event_hash": e.previous_event_hash,
         "event_hash": e.event_hash, "created_at": e.created_at.isoformat()} for e in events]}


class PointInTimeLinkInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    as_of: datetime


@router.post("/business-quality/assessments/{assessment_id}/evidence-links", status_code=201)
async def create_assessment_evidence_links(assessment_id: UUID, payload: PointInTimeLinkInput,
                                           session: AsyncSession = Depends(get_db_session)) -> dict:
    assessment = await session.get(BusinessQualityAssessment, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if payload.as_of.tzinfo is None or payload.as_of.utcoffset() is None:
        raise HTTPException(status_code=422, detail="as_of must include timezone")
    if await session.scalar(select(BQAssessmentEvidenceLink.id).where(
        BQAssessmentEvidenceLink.assessment_id == assessment_id).limit(1)):
        raise HTTPException(status_code=409, detail="Evidence links already exist; create a new assessment to relink")
    candidates = list((await session.scalars(select(BQEvidenceCandidate).where(
        BQEvidenceCandidate.company_id == assessment.company_id))).all())
    records = []
    candidate_by_id = {str(c.id): c for c in candidates if c.status == "VERIFIED"}
    documents = {}
    for candidate in candidate_by_id.values():
        doc = await session.get(BQSourceDocument, candidate.document_id)
        if doc is None:
            continue
        documents[str(candidate.id)] = doc
        records.append(EvidenceRecord(evidence_id=str(candidate.id), criterion_key=candidate.criterion_key,
            source_name=f"SEC {doc.form_type} {doc.accession_number}", source_url=doc.source_url,
            published_at=doc.published_at, available_at=doc.published_at,
            captured_at=candidate.created_at, content_hash=candidate.evidence_hash, source_type="SEC_FILING"))
    try:
        decisions = {d.evidence_id: d for d in evaluate_point_in_time_evidence(records, as_of=payload.as_of)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    now = datetime.now(UTC)
    output = []
    for candidate in candidates:
        decision = decisions.get(str(candidate.id))
        if candidate.status != "VERIFIED":
            eligible, reason = False, "EVIDENCE_NOT_VERIFIED"
        elif decision is None:
            eligible, reason = False, "SOURCE_DOCUMENT_UNAVAILABLE"
        else:
            eligible, reason = decision.eligible, decision.reason
        session.add(BQAssessmentEvidenceLink(assessment_id=assessment_id, candidate_id=candidate.id,
            as_of=payload.as_of, eligible=eligible, decision_reason=reason,
            policy_version="PIT_EVIDENCE_1.0.0", evidence_hash=candidate.evidence_hash, created_at=now))
        output.append({"candidate_id": str(candidate.id), "eligible": eligible, "reason": reason})
    await session.commit()
    return {"assessment_id": str(assessment_id), "as_of": payload.as_of.isoformat(),
            "policy_version": "PIT_EVIDENCE_1.0.0", "links": output}


@router.get("/business-quality/assessments/{assessment_id}/evidence-links")
async def list_assessment_evidence_links(assessment_id: UUID,
                                         session: AsyncSession = Depends(get_db_session)) -> dict:
    if await session.get(BusinessQualityAssessment, assessment_id) is None:
        raise HTTPException(status_code=404, detail="Assessment not found")
    links = list((await session.scalars(select(BQAssessmentEvidenceLink).where(
        BQAssessmentEvidenceLink.assessment_id == assessment_id).order_by(BQAssessmentEvidenceLink.created_at))).all())
    return {"assessment_id": str(assessment_id), "links": [
        {"candidate_id": str(x.candidate_id), "as_of": x.as_of.isoformat(), "eligible": x.eligible,
         "reason": x.decision_reason, "policy_version": x.policy_version, "evidence_hash": x.evidence_hash}
        for x in links]}

@router.get("/business-quality/criteria")
async def list_business_quality_criteria() -> dict:
    """Expose the versioned scoring rubric and its non-authoritative retrieval cues."""
    return {
        "rubric_version": "business-quality-v1.0.0",
        "extraction_version": EXTRACTION_VERSION,
        "criteria": [
            {"criterion_key": item.criterion_key, "dimension": item.dimension,
             "label": item.label, "weight": item.weight, "required": item.required,
             "retrieval_cues": list(item.retrieval_cues)}
            for item in criterion_catalog()
        ],
        "notice": "Retrieval cues locate candidate passages; they do not establish truth or score a criterion.",
    }


@router.post("/business-quality/document-sections/{section_id}/extract-candidates")
async def extract_bq_section_candidates(
    section_id: UUID,
    max_candidates: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Preview candidate passages from a persisted section without approving or scoring them."""
    section = await session.get(BQDocumentSection, section_id)
    if section is None:
        raise HTTPException(status_code=404, detail="Document section not found")
    passages = extract_evidence_candidates(
        section.text_content, section_key=section.section_key, max_candidates=max_candidates,
    )
    conflicts = detect_potential_conflicts(passages)
    return {
        "section_id": str(section.id),
        "document_id": str(section.document_id),
        "extraction_version": EXTRACTION_VERSION,
        "candidate_count": len(passages),
        "candidates": [
            {"criterion_key": item.criterion_key, "dimension": item.dimension,
             "passage": item.passage, "source_locator": item.source_locator,
             "passage_type": item.passage_type, "matched_cues": list(item.matched_cues),
             "rationale": item.rationale, "status": "CANDIDATE"}
            for item in passages
        ],
        "potential_conflicts": list(conflicts),
        "review_required": True,
        "scores_generated": False,
    }


@router.get("/business-quality/companies/{company_id}/source-documents")
async def list_bq_source_documents(
    company_id: UUID, limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """List document metadata for the evidence review workspace; never returns raw bytes."""
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    rows = list((await session.scalars(select(BQSourceDocument).where(
        BQSourceDocument.company_id == company_id
    ).order_by(BQSourceDocument.filed_at.desc()).limit(limit))).all())
    return {"company_id": str(company_id), "documents": [
        {"id": str(row.id), "accession_number": row.accession_number, "form_type": row.form_type,
         "filed_at": row.filed_at.isoformat(),
         "published_at": row.published_at.isoformat() if row.published_at else None,
         "source_url": row.source_url, "content_type": row.content_type,
         "document_hash": row.document_hash, "extraction_version": row.extraction_version}
        for row in rows
    ]}


@router.get("/business-quality/source-documents/{document_id}/sections")
async def list_bq_document_sections(
    document_id: UUID, session: AsyncSession = Depends(get_db_session),
) -> dict:
    document = await session.get(BQSourceDocument, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Source document not found")
    rows = list((await session.scalars(select(BQDocumentSection).where(
        BQDocumentSection.document_id == document_id
    ).order_by(BQDocumentSection.sequence_number))).all())
    return {"document_id": str(document_id), "sections": [
        {"id": str(row.id), "section_key": row.section_key, "heading": row.heading,
         "sequence_number": row.sequence_number, "text_content": row.text_content,
         "content_hash": row.content_hash, "extraction_method": row.extraction_method}
        for row in rows
    ]}


@router.get("/business-quality/companies/{company_id}/evidence-candidates")
async def list_bq_evidence_candidates(
    company_id: UUID,
    status_filter: str | None = Query(default=None, alias="status", pattern="^(CANDIDATE|VERIFIED|REJECTED|SUPERSEDED)$"),
    criterion_key: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    if await session.get(Company, company_id) is None:
        raise HTTPException(status_code=404, detail="Company not found")
    statement = select(BQEvidenceCandidate).where(BQEvidenceCandidate.company_id == company_id)
    if status_filter:
        statement = statement.where(BQEvidenceCandidate.status == status_filter)
    if criterion_key:
        statement = statement.where(BQEvidenceCandidate.criterion_key == criterion_key)
    rows = list((await session.scalars(statement.order_by(
        BQEvidenceCandidate.created_at.desc()).offset(offset).limit(limit))).all())
    return {"company_id": str(company_id), "count": len(rows), "limit": limit, "offset": offset,
        "candidates": [{"id": str(row.id), "criterion_key": row.criterion_key,
            "status": row.status, "passage": row.passage, "rationale": row.rationale,
            "source_locator": row.source_locator, "evidence_hash": row.evidence_hash,
            "created_by": row.created_by, "reviewed_by": row.reviewed_by,
            "review_comment": row.review_comment, "created_at": row.created_at.isoformat(),
            "document_id": str(row.document_id), "section_id": str(row.section_id) if row.section_id else None}
            for row in rows]}


@router.get("/business-quality/evidence-candidates/{candidate_id}")
async def get_bq_evidence_candidate(
    candidate_id: UUID, session: AsyncSession = Depends(get_db_session),
) -> dict:
    item = await session.get(BQEvidenceCandidate, candidate_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence candidate not found")
    document = await session.get(BQSourceDocument, item.document_id)
    section = await session.get(BQDocumentSection, item.section_id) if item.section_id else None
    events = list((await session.scalars(select(BQEvidenceReviewEvent).where(
        BQEvidenceReviewEvent.candidate_id == candidate_id
    ).order_by(BQEvidenceReviewEvent.created_at, BQEvidenceReviewEvent.id))).all())
    return {"id": str(item.id), "company_id": str(item.company_id), "criterion_key": item.criterion_key,
        "status": item.status, "passage": item.passage, "rationale": item.rationale,
        "source_locator": item.source_locator, "evidence_hash": item.evidence_hash,
        "created_by": item.created_by, "reviewed_by": item.reviewed_by,
        "review_comment": item.review_comment, "created_at": item.created_at.isoformat(),
        "document": ({"id": str(document.id), "form_type": document.form_type,
            "accession_number": document.accession_number, "filed_at": document.filed_at.isoformat(),
            "published_at": document.published_at.isoformat() if document.published_at else None,
            "source_url": document.source_url, "document_hash": document.document_hash}
            if document else None),
        "section": ({"id": str(section.id), "section_key": section.section_key,
            "heading": section.heading, "text_content": section.text_content,
            "content_hash": section.content_hash} if section else None),
        "review_events": [{"id": str(event.id), "from_status": event.from_status,
            "to_status": event.to_status, "actor_id": event.actor_id, "comment": event.comment,
            "previous_event_hash": event.previous_event_hash, "event_hash": event.event_hash,
            "created_at": event.created_at.isoformat()} for event in events]}


async def _assemble_company_research_brief(
    *, company_id: UUID, session: AsyncSession, as_of: date | None,
    document_limit: int, max_passages: int,
) -> dict:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    statement = select(BQSourceDocument).where(BQSourceDocument.company_id == company_id)
    if as_of is not None:
        statement = statement.where(BQSourceDocument.filed_at <= datetime.combine(
            as_of, datetime.max.time(), tzinfo=UTC
        ))
    docs = list((await session.scalars(statement.order_by(
        BQSourceDocument.filed_at.desc(), BQSourceDocument.id.desc()
    ).limit(document_limit))).all())
    doc_ids = [doc.id for doc in docs]
    sections_by_doc: dict[UUID, list[BQDocumentSection]] = {doc_id: [] for doc_id in doc_ids}
    if doc_ids:
        sections = list((await session.scalars(select(BQDocumentSection).where(
            BQDocumentSection.document_id.in_(doc_ids)
        ).order_by(BQDocumentSection.document_id, BQDocumentSection.sequence_number))).all())
        for section in sections:
            sections_by_doc[section.document_id].append(section)
    research_docs = tuple(
        ResearchDocument(
            document_id=str(doc.id), accession_number=doc.accession_number,
            form_type=doc.form_type, filed_at=doc.filed_at, published_at=doc.published_at,
            source_url=doc.source_url, document_hash=doc.document_hash,
            sections=tuple(ResearchSection(
                section_id=str(section.id), section_key=section.section_key,
                heading=section.heading, sequence_number=section.sequence_number,
                text_content=section.text_content,
            ) for section in sections_by_doc[doc.id]),
        ) for doc in docs
    )
    return build_research_brief(
        company_id=str(company.id), company_name=company.display_name or company.legal_name,
        documents=research_docs, as_of=as_of, max_passages=max_passages,
    )


@router.get("/research/companies/{company_id}/brief")
async def get_company_research_brief(
    company_id: UUID,
    as_of: date | None = Query(default=None),
    document_limit: int = Query(default=50, ge=1, le=100),
    max_passages: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Assemble a citation-first brief from already ingested SEC filing sections."""
    return await _assemble_company_research_brief(
        company_id=company_id, session=session, as_of=as_of,
        document_limit=document_limit, max_passages=max_passages,
    )


class ResearchCopilotInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=3, max_length=4000)
    as_of: date | None = None
    document_limit: int = Field(default=30, ge=1, le=50)
    max_passages: int = Field(default=120, ge=1, le=500)


@router.post("/research/companies/{company_id}/copilot")
async def ask_company_research_copilot(
    company_id: UUID, payload: ResearchCopilotInput,
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Answer a company research question using only previously ingested SEC evidence."""
    settings = get_settings()
    if not settings.openai_enabled:
        raise HTTPException(status_code=503, detail="AI research provider is not enabled")
    brief = await _assemble_company_research_brief(
        company_id=company_id, session=session, as_of=payload.as_of,
        document_limit=payload.document_limit, max_passages=payload.max_passages,
    )
    model = OpenAIResponsesModel(
        api_key=settings.openai_api_key.get_secret_value(), model=settings.openai_model,
        base_url=settings.openai_base_url, timeout_seconds=settings.openai_timeout_seconds,
        max_output_tokens=settings.openai_max_output_tokens,
    )
    try:
        result = await answer_research_question(
            question=payload.question, brief=brief, model=model,
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="AI response failed citation or schema validation") from exc
    except ResearchProviderError as exc:
        status_code = 503 if exc.retryable else 502
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    return {
        "company_id": str(company_id),
        "company_name": brief["company_name"],
        "brief_version": brief["brief_version"],
        "source_document_count": brief["source_document_count"],
        "result": result,
        "provider": "openai-responses",
        "model": settings.openai_model,
        "disclaimer": "Research assistance only; not investment advice. Model output does not modify deterministic scores or valuation.",
    }


@router.get("/research/companies/{company_id}/what-changed")
async def get_company_what_changed(
    company_id: UUID,
    from_date: date = Query(...),
    to_date: date = Query(...),
    document_limit: int = Query(default=50, ge=1, le=100),
    max_passages: int = Query(default=200, ge=1, le=1000),
    session: AsyncSession = Depends(get_db_session),
) -> dict:
    """Compare ingested filing evidence and latest BQ snapshots at two date cutoffs."""
    if from_date >= to_date:
        raise HTTPException(status_code=422, detail="from_date must be earlier than to_date")
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    before_brief = await _assemble_company_research_brief(
        company_id=company_id, session=session, as_of=from_date,
        document_limit=document_limit, max_passages=max_passages,
    )
    after_brief = await _assemble_company_research_brief(
        company_id=company_id, session=session, as_of=to_date,
        document_limit=document_limit, max_passages=max_passages,
    )

    async def latest_assessment(cutoff: date) -> dict | None:
        cutoff_dt = datetime.combine(cutoff, datetime.max.time(), tzinfo=UTC)
        record = await session.scalar(
            select(BusinessQualityAssessment)
            .where(
                BusinessQualityAssessment.company_id == company_id,
                BusinessQualityAssessment.created_at <= cutoff_dt,
            )
            .order_by(BusinessQualityAssessment.created_at.desc(), BusinessQualityAssessment.id.desc())
            .limit(1)
        )
        if record is None:
            return None
        return {
            "id": str(record.id),
            "created_at": record.created_at.isoformat(),
            "engine_version": record.engine_version,
            "rubric_version": record.rubric_version,
            "status": record.status,
            "overall_score": str(record.overall_score) if record.overall_score is not None else None,
            "classification": record.classification,
            "results": record.results,
        }

    before_assessment = await latest_assessment(from_date)
    after_assessment = await latest_assessment(to_date)
    return build_what_changed(
        company_id=str(company.id),
        company_name=company.display_name or company.legal_name,
        from_date=from_date,
        to_date=to_date,
        before_brief=before_brief,
        after_brief=after_brief,
        before_assessment=before_assessment,
        after_assessment=after_assessment,
    )
