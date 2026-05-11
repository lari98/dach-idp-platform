"""
app/api/invoices.py
====================
Invoice API endpoints.

POST  /api/v1/invoices/upload       — Upload and extract invoice
GET   /api/v1/invoices/             — List all invoices
GET   /api/v1/invoices/{id}         — Get single invoice result
PATCH /api/v1/invoices/{id}/review  — Submit manual review decision
DELETE /api/v1/invoices/{id}        — GDPR Art. 17 erasure
GET   /api/v1/invoices/{id}/audit   — Audit trail for document
"""
from __future__ import annotations

import uuid
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models.gdpr import AuditAction, DocumentType
from app.models.invoice import (
    InvoiceExtractionResult,
    InvoiceListItem,
    InvoiceUploadResponse,
    ReviewStatus,
)
from app.services.audit_service import AuditService
from app.services.blob_storage import BlobStorageService
from app.services.gdpr_service import GDPRService
from app.services.invoice_extractor import InvoiceExtractor

log = structlog.get_logger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])

# Dependency singletons (in production, use FastAPI DI with proper lifecycle)
_blob_service = BlobStorageService()
_extractor = InvoiceExtractor()
_audit_service = AuditService()
_gdpr_service = GDPRService(audit_service=_audit_service)

# In-memory store for demo (replace with DB in production)
_invoice_store: dict = {}


def _get_actor_id(request: Request) -> str:
    """Extract actor ID from request. In production: parse JWT."""
    return request.headers.get("X-User-ID", "anonymous")


@router.post(
    "/upload",
    response_model=InvoiceUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload and extract an invoice PDF",
    description=(
        "Upload a PDF invoice. The system extracts structured data using "
        "Azure AI Document Intelligence (or mock mode). "
        "Supports German, English, French, and Italian. "
        "Returns a document_id for async polling.\n\n"
        "**GDPR**: Uploading constitutes consent for invoice processing under "
        "DSGVO Art. 6(1)(b) (contract performance). "
        "Provide consent_id to link an explicit consent record."
    ),
)
async def upload_invoice(
    request: Request,
    file: UploadFile = File(..., description="PDF file, max 20MB"),
    consent_id: Optional[str] = Form(None, description="GDPR consent record ID"),
):
    # ── Validation ─────────────────────────────────────────────────────────
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted.",
        )

    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20MB
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds 20MB limit.",
        )
    if len(content) < 100:
        raise HTTPException(status_code=400, detail="File appears to be empty or corrupt.")

    actor_id = _get_actor_id(request)
    document_id = f"inv-{uuid.uuid4().hex[:12]}"

    # ── Upload to storage ──────────────────────────────────────────────────
    doc_id, blob_url = await _blob_service.upload_document(
        file_bytes=content,
        original_filename=file.filename,
        document_type="invoice",
        document_id=document_id,
    )

    await _audit_service.log(
        action=AuditAction.UPLOAD,
        document_id=document_id,
        document_type=DocumentType.INVOICE,
        actor_id=actor_id,
        actor_role="user",
        details={"filename": file.filename, "size_bytes": len(content)},
    )

    # ── Extract ────────────────────────────────────────────────────────────
    result = await _extractor.extract(
        blob_url=blob_url,
        document_id=document_id,
        original_filename=file.filename,
        consent_id=consent_id,
    )

    # Store result
    _invoice_store[document_id] = result

    await _audit_service.log(
        action=AuditAction.EXTRACT,
        document_id=document_id,
        document_type=DocumentType.INVOICE,
        actor_id=actor_id,
        actor_role="system",
        details={
            "overall_confidence": result.overall_confidence,
            "requires_review": result.requires_manual_review,
            "mode": settings.app_mode.value,
        },
    )

    log.info("invoice_uploaded_and_extracted", document_id=document_id)

    return InvoiceUploadResponse(
        document_id=document_id,
        message=(
            f"Invoice processed successfully in {settings.app_mode.value} mode. "
            f"Confidence: {result.overall_confidence:.0%}. "
            + ("Manual review required." if result.requires_manual_review else "Auto-approved.")
        ),
        mode=settings.app_mode.value,
        status="complete",
    )


@router.get(
    "/",
    response_model=List[InvoiceListItem],
    summary="List all processed invoices",
)
async def list_invoices(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    requires_review: Optional[bool] = None,
    country: Optional[str] = None,
):
    await _audit_service.log(
        action=AuditAction.VIEW,
        actor_id=_get_actor_id(request),
        actor_role="user",
        details={"endpoint": "list_invoices"},
    )

    results = list(_invoice_store.values())

    if requires_review is not None:
        results = [r for r in results if r.requires_manual_review == requires_review]
    if country:
        results = [r for r in results if r.country_detected and r.country_detected.value == country.upper()]

    items = []
    for r in results[skip : skip + limit]:
        items.append(
            InvoiceListItem(
                document_id=r.document_id,
                original_filename=r.original_filename,
                uploaded_at=r.uploaded_at,
                vendor_name=r.vendor_name.value if r.vendor_name else None,
                total_gross=r.total_gross,
                currency=r.currency.value if r.currency else None,
                requires_manual_review=r.requires_manual_review,
                review_status=r.review_status,
                language_detected=r.language_detected,
                country_detected=r.country_detected.value if r.country_detected else None,
            )
        )
    return items


@router.get(
    "/{document_id}",
    response_model=InvoiceExtractionResult,
    summary="Get extraction result for a specific invoice",
)
async def get_invoice(document_id: str, request: Request):
    result = _invoice_store.get(document_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Invoice '{document_id}' not found.")

    await _audit_service.log(
        action=AuditAction.VIEW,
        document_id=document_id,
        document_type=DocumentType.INVOICE,
        actor_id=_get_actor_id(request),
        actor_role="user",
    )
    return result


@router.patch(
    "/{document_id}/review",
    summary="Submit manual review decision",
    description="Approve or reject an invoice that requires manual review.",
)
async def submit_review(
    document_id: str,
    request: Request,
    decision: str = Form(..., description="'approved' or 'rejected'"),
    notes: Optional[str] = Form(None),
):
    result = _invoice_store.get(document_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Invoice '{document_id}' not found.")

    if decision not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'approved' or 'rejected'.")

    result.review_status = ReviewStatus.APPROVED if decision == "approved" else ReviewStatus.REJECTED
    result.review_notes = notes
    result.requires_manual_review = False

    action = AuditAction.REVIEW_APPROVED if decision == "approved" else AuditAction.REVIEW_REJECTED
    await _audit_service.log(
        action=action,
        document_id=document_id,
        document_type=DocumentType.INVOICE,
        actor_id=_get_actor_id(request),
        actor_role="reviewer",
        details={"decision": decision, "notes": notes},
    )

    return {"document_id": document_id, "review_status": result.review_status, "notes": notes}


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="GDPR Art. 17 — Erase invoice data",
    description=(
        "Delete all data associated with this invoice document. "
        "Blob is deleted from storage. DB record is anonymised. "
        "Audit trail is retained as required by DSGVO accountability principle."
    ),
)
async def delete_invoice(document_id: str, request: Request):
    result = _invoice_store.get(document_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Invoice '{document_id}' not found.")

    # Delete from blob storage
    if result.blob_url:
        await _blob_service.delete_blob(result.blob_url)

    # Remove from in-memory store (in prod: anonymise DB record)
    del _invoice_store[document_id]

    await _audit_service.log(
        action=AuditAction.DELETE,
        document_id=document_id,
        document_type=DocumentType.INVOICE,
        actor_id=_get_actor_id(request),
        actor_role="user",
        details={"reason": "GDPR Art. 17 erasure request"},
    )

    return {
        "document_id": document_id,
        "status": "deleted",
        "message": (
            "All invoice data and associated blob have been deleted. "
            "Audit records are retained as required by DSGVO Art. 5(2)."
        ),
    }


@router.get(
    "/{document_id}/audit",
    summary="Get full audit trail for an invoice",
    description="Returns all audit log entries for this document. Admin access only.",
)
async def get_audit_trail(document_id: str, request: Request):
    logs = await _audit_service.get_logs(document_id=document_id)
    return {
        "document_id": document_id,
        "audit_entries": [entry.model_dump(mode="json") for entry in logs],
        "total": len(logs),
    }
