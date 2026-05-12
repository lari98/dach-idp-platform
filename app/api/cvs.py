"""
app/api/cvs.py
===============
CV/Resume API endpoints.

POST  /api/v1/cvs/upload          — Upload and extract CV
GET   /api/v1/cvs/                — List all CVs
GET   /api/v1/cvs/{id}            — Get CV extraction result
POST  /api/v1/cvs/{id}/score      — Re-score against a job description
GET   /api/v1/cvs/{id}/recruiter  — Get recruiter summary
PATCH /api/v1/cvs/{id}/mask-pii   — Mask PII in CV record
DELETE /api/v1/cvs/{id}           — GDPR Art. 17 erasure
"""
from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from app.config import get_settings
from app.models.cv import CVExtractionResult, CVListItem, CVUploadResponse
from app.models.gdpr import AuditAction, DocumentType
from app.services.audit_service import AuditService
from app.services.blob_storage import BlobStorageService
from app.services.cv_extractor import CVExtractor
from app.services.gdpr_service import GDPRService
from app.services.pii_masker import PIIMasker

log = structlog.get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/v1/cvs", tags=["CVs / Resumes"])

_blob_service = BlobStorageService()
_extractor = CVExtractor()
_audit_service = AuditService()
_gdpr_service = GDPRService(audit_service=_audit_service)
_pii_masker = PIIMasker()

_cv_store: dict = {}


def _get_actor_id(request: Request) -> str:
    return request.headers.get("X-User-ID", "anonymous")


@router.post(
    "/upload",
    response_model=CVUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and extract a CV/resume PDF",
    description=(
        "Upload a CV/resume PDF. Extracts structured candidate data, "
        "computes ATS score (if job description provided), "
        "generates recruiter summary and DACH eligibility note.\n\n"
        "**GDPR**: Candidate data is processed under Art. 6(1)(b) or (a). "
        "Provide a consent_id for explicit consent tracking."
    ),
)
async def upload_cv(
    request: Request,
    file: UploadFile = File(..., description="PDF file, max 10MB"),
    job_description: Optional[str] = Form(None, description="Job description text for ATS scoring"),
    consent_id: Optional[str] = Form(None, description="GDPR consent record ID"),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted.",
        )

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 10MB limit.")
    if len(content) < 100:
        raise HTTPException(status_code=400, detail="File appears to be empty or corrupt.")

    actor_id = _get_actor_id(request)
    document_id = f"cv-{uuid.uuid4().hex[:12]}"

    doc_id, blob_url = await _blob_service.upload_document(
        file_bytes=content,
        original_filename=file.filename,
        document_type="cv",
        document_id=document_id,
    )

    await _audit_service.log(
        action=AuditAction.UPLOAD,
        document_id=document_id,
        document_type=DocumentType.CV,
        actor_id=actor_id,
        actor_role="user",
        details={"filename": file.filename, "size_bytes": len(content), "jd_provided": bool(job_description)},
    )

    result = await _extractor.extract(
        blob_url=blob_url,
        document_id=document_id,
        original_filename=file.filename,
        job_description=job_description,
        consent_id=consent_id,
    )

    _cv_store[document_id] = result

    await _audit_service.log(
        action=AuditAction.EXTRACT,
        document_id=document_id,
        document_type=DocumentType.CV,
        actor_id=actor_id,
        actor_role="system",
        details={
            "overall_confidence": result.overall_confidence,
            "ats_score": result.ats_score.score if result.ats_score else None,
            "mode": settings.app_mode.value,
        },
    )

    return CVUploadResponse(
        document_id=document_id,
        message=(
            f"CV processed in {settings.app_mode.value} mode. "
            f"Confidence: {result.overall_confidence:.0%}. "
            + (f"ATS score: {result.ats_score.score:.0f}/100." if result.ats_score else "")
        ),
        mode=settings.app_mode.value,
        status="complete",
    )


@router.get(
    "/",
    response_model=List[CVListItem],
    summary="List all processed CVs",
)
async def list_cvs(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    role_category: Optional[str] = None,
    min_ats_score: Optional[float] = None,
    pii_masked: Optional[bool] = None,
):
    results = list(_cv_store.values())

    if role_category:
        results = [r for r in results if r.target_role_category and r.target_role_category.value == role_category]
    if min_ats_score is not None:
        results = [r for r in results if r.ats_score and r.ats_score.score >= min_ats_score]
    if pii_masked is not None:
        results = [r for r in results if r.pii_masked == pii_masked]

    items = []
    for r in results[skip : skip + limit]:
        items.append(
            CVListItem(
                document_id=r.document_id,
                original_filename=r.original_filename,
                uploaded_at=r.uploaded_at,
                full_name="[MASKED]" if r.pii_masked else r.full_name,
                current_title=r.current_title,
                years_of_experience=r.years_of_experience,
                ats_score=r.ats_score.score if r.ats_score else None,
                target_role_category=r.target_role_category.value if r.target_role_category else None,
                requires_manual_review=r.requires_manual_review,
                pii_masked=r.pii_masked,
            )
        )
    return items


@router.get(
    "/{document_id}",
    response_model=CVExtractionResult,
    summary="Get CV extraction result",
)
async def get_cv(document_id: str, request: Request):
    result = _cv_store.get(document_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"CV '{document_id}' not found.")

    await _audit_service.log(
        action=AuditAction.VIEW,
        document_id=document_id,
        document_type=DocumentType.CV,
        actor_id=_get_actor_id(request),
        actor_role="user",
    )
    return result


@router.post(
    "/{document_id}/score",
    summary="Re-score CV against a new job description",
    description="Provide a job description to compute or refresh the ATS match score.",
)
async def score_cv(
    document_id: str,
    request: Request,
    job_description: str = Form(..., description="Job description text"),
):
    result = _cv_store.get(document_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"CV '{document_id}' not found.")

    ats_score = _extractor._compute_ats_score(result, job_description)
    result.ats_score = ats_score

    return {
        "document_id": document_id,
        "ats_score": ats_score.model_dump(),
    }


@router.get(
    "/{document_id}/recruiter",
    summary="Get recruiter summary for a CV",
    description=(
        "Returns the AI-generated recruiter summary and improvement suggestions. "
        "Intended for internal recruiter notes only. "
        "Must not be shared with the candidate without their consent (GDPR Art. 22)."
    ),
)
async def get_recruiter_summary(document_id: str, request: Request):
    result = _cv_store.get(document_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"CV '{document_id}' not found.")

    await _audit_service.log(
        action=AuditAction.VIEW,
        document_id=document_id,
        document_type=DocumentType.CV,
        actor_id=_get_actor_id(request),
        actor_role="recruiter",
        details={"view_type": "recruiter_summary"},
    )

    return {
        "document_id": document_id,
        "recruiter_summary": result.recruiter_summary,
        "improvement_suggestions": result.candidate_improvement_suggestions,
        "dach_work_eligibility_note": result.dach_work_eligibility_note,
        "dach_work_eligibility_classification": result.dach_work_eligibility_classification,
        "ats_score": result.ats_score.model_dump() if result.ats_score else None,
        "gdpr_notice": (
            "This AI-generated summary is for internal recruiter use only. "
            "It must not be used as the sole basis for hiring decisions (GDPR Art. 22 — automated decision-making). "
            "Human review is required before communicating outcomes to candidates."
        ),
    }


@router.patch(
    "/{document_id}/mask-pii",
    summary="Mask PII fields in a CV record",
    description=(
        "Apply pseudonymisation to PII fields (name, email, phone, DOB, nationality). "
        "Masking is irreversible without the encryption key. "
        "Use for GDPR Art. 25 — data protection by design."
    ),
)
async def mask_pii(document_id: str, request: Request):
    result = _cv_store.get(document_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"CV '{document_id}' not found.")

    if result.pii_masked:
        return {"document_id": document_id, "status": "already_masked"}

    # Apply masking to PII fields
    result.full_name = "[MASKED]" if result.full_name else None
    result.email = "[MASKED]" if result.email else None
    result.phone = "[MASKED]" if result.phone else None
    result.date_of_birth = "[MASKED]" if result.date_of_birth else None
    result.nationality = "[MASKED]" if result.nationality else None
    result.linkedin_url = "[MASKED]" if result.linkedin_url else None
    result.pii_masked = True

    await _audit_service.log(
        action=AuditAction.MASK_PII,
        document_id=document_id,
        document_type=DocumentType.CV,
        actor_id=_get_actor_id(request),
        actor_role="system",
        details={"fields_masked": ["full_name", "email", "phone", "date_of_birth", "nationality", "linkedin_url"]},
    )

    return {"document_id": document_id, "status": "pii_masked", "fields_masked": 6}


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="GDPR Art. 17 — Erase CV data",
)
async def delete_cv(document_id: str, request: Request):
    result = _cv_store.get(document_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"CV '{document_id}' not found.")

    if result.blob_url:
        await _blob_service.delete_blob(result.blob_url)

    del _cv_store[document_id]

    await _audit_service.log(
        action=AuditAction.DELETE,
        document_id=document_id,
        document_type=DocumentType.CV,
        actor_id=_get_actor_id(request),
        actor_role="user",
        details={"reason": "GDPR Art. 17 erasure"},
    )

    return {
        "document_id": document_id,
        "status": "deleted",
        "message": "CV data deleted. Audit records retained per DSGVO Art. 5(2).",
    }


@router.get(
    "/{document_id}/audit",
    summary="Get audit trail for a CV",
)
async def get_audit_trail(document_id: str, request: Request):
    logs = await _audit_service.get_logs(document_id=document_id)
    return {
        "document_id": document_id,
        "audit_entries": [entry.model_dump(mode="json") for entry in logs],
        "total": len(logs),
    }
