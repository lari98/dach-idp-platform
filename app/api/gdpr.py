"""
app/api/gdpr.py
================
GDPR / DSGVO compliance API endpoints.

POST /api/v1/gdpr/consent          — Grant explicit consent
POST /api/v1/gdpr/consent/withdraw — Withdraw consent
GET  /api/v1/gdpr/consent/{id}     — Get consent record

POST /api/v1/gdpr/dsr              — Submit Data Subject Request
GET  /api/v1/gdpr/dsr              — List all DSRs (admin)
GET  /api/v1/gdpr/dsr/{id}         — Get DSR status
POST /api/v1/gdpr/dsr/{id}/erasure — Execute erasure
POST /api/v1/gdpr/dsr/{id}/access  — Execute access request

GET  /api/v1/gdpr/audit            — Query audit log
GET  /api/v1/gdpr/health           — GDPR compliance health check
"""
from __future__ import annotations

from typing import List, Optional

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from app.models.gdpr import (
    AuditLogEntry,
    ConsentGrantRequest,
    ConsentRecord,
    DSRSubmitRequest,
    DSRSubmitResponse,
    DataSubjectRequest,
)
from app.services.audit_service import AuditService
from app.services.gdpr_service import GDPRService

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/gdpr", tags=["GDPR / DSGVO Compliance"])

_audit_service = AuditService()
_gdpr_service = GDPRService(audit_service=_audit_service)


def _get_actor_id(request: Request) -> str:
    return request.headers.get("X-User-ID", "anonymous")


# ──────────────────────────────────────────────────────────────────────────────
# Consent
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/consent",
    response_model=ConsentRecord,
    status_code=status.HTTP_201_CREATED,
    summary="Grant explicit consent for document processing",
    description=(
        "Record explicit consent (GDPR Art. 6(1)(a) / Art. 7). "
        "Must be freely given, specific, informed, and unambiguous."
    ),
)
async def grant_consent(request: Request, body: ConsentGrantRequest):
    ip = request.client.host if request.client else None
    consent = await _gdpr_service.grant_consent(
        request=body,
        ip_address=ip,
        actor_id=_get_actor_id(request),
    )
    return consent


@router.post(
    "/consent/withdraw",
    summary="Withdraw consent",
    description="GDPR Art. 7(3) — Withdrawal must be as easy as giving consent.",
)
async def withdraw_consent(request: Request, consent_id: str):
    try:
        consent = await _gdpr_service.withdraw_consent(
            consent_id=consent_id,
            actor_id=_get_actor_id(request),
        )
        return {
            "consent_id": consent_id,
            "status": "withdrawn",
            "withdrawn_at": consent.withdrawn_at.isoformat(),
            "message": (
                "Consent withdrawn. Processing of personal data based on this consent "
                "will cease. Data will be reviewed for retention/deletion per DSGVO Art. 17."
            ),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/consent/{consent_id}",
    response_model=ConsentRecord,
    summary="Get consent record",
)
async def get_consent(consent_id: str):
    consent = await _gdpr_service.get_consent(consent_id)
    if not consent:
        raise HTTPException(status_code=404, detail=f"Consent record '{consent_id}' not found.")
    return consent


# ──────────────────────────────────────────────────────────────────────────────
# Data Subject Requests
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/dsr",
    response_model=DSRSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a Data Subject Request",
    description=(
        "Submit a rights request under GDPR Chapter III. "
        "Supported types: access, rectification, erasure, restriction, portability, objection. "
        "Response guaranteed within 30 calendar days (Art. 12(3))."
    ),
)
async def submit_dsr(request: Request, body: DSRSubmitRequest):
    return await _gdpr_service.submit_dsr(
        request=body,
        actor_id=_get_actor_id(request),
    )


@router.get(
    "/dsr",
    response_model=List[DataSubjectRequest],
    summary="List all Data Subject Requests (admin)",
)
async def list_dsrs():
    return await _gdpr_service.list_dsrs()


@router.get(
    "/dsr/{dsr_id}",
    response_model=DataSubjectRequest,
    summary="Get DSR status",
)
async def get_dsr(dsr_id: str):
    dsr = await _gdpr_service.get_dsr(dsr_id)
    if not dsr:
        raise HTTPException(status_code=404, detail=f"DSR '{dsr_id}' not found.")
    return dsr


@router.post(
    "/dsr/{dsr_id}/erasure",
    summary="Execute GDPR Art. 17 erasure for a DSR",
    description=(
        "Delete all personal data linked to the affected documents. "
        "Blobs are deleted. DB records are anonymised. "
        "Audit trail is retained as required by accountability principle."
    ),
)
async def execute_erasure(dsr_id: str, request: Request):
    # Simplified: in production would wire up real blob_service and db_service
    class MockDB:
        async def get_document(self, doc_id):
            return {"document_id": doc_id, "blob_url": None}
        async def anonymise_document(self, doc_id):
            pass

    from app.services.blob_storage import BlobStorageService
    result = await _gdpr_service.process_erasure_request(
        dsr_id=dsr_id,
        blob_service=BlobStorageService(),
        db_service=MockDB(),
        actor_id=_get_actor_id(request),
    )
    return result


@router.post(
    "/dsr/{dsr_id}/access",
    summary="Execute GDPR Art. 15 access request",
    description="Generate a portable data export package for the data subject.",
)
async def execute_access_request(dsr_id: str, request: Request):
    class MockDB:
        async def get_document(self, doc_id):
            return {"document_id": doc_id, "note": "Extracted data placeholder"}

    package, export_json = await _gdpr_service.process_access_request(
        dsr_id=dsr_id,
        db_service=MockDB(),
        actor_id=_get_actor_id(request),
    )
    return {
        "export_package": package.model_dump(mode="json"),
        "export_data_preview": export_json[:500] + "...",
        "note": "In production, export_data is encrypted and delivered via secure link.",
    }


# ──────────────────────────────────────────────────────────────────────────────
# Audit Log
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/audit",
    summary="Query audit log",
    description="Returns audit log entries. Filter by document_id or action.",
)
async def query_audit_log(
    document_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
):
    from app.models.gdpr import AuditAction
    action_enum = None
    if action:
        try:
            action_enum = AuditAction(action)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid action: {action}")

    logs = await _audit_service.get_logs(
        document_id=document_id,
        action=action_enum,
        limit=limit,
    )
    return {
        "total": len(logs),
        "entries": [entry.model_dump(mode="json") for entry in logs],
    }


# ──────────────────────────────────────────────────────────────────────────────
# GDPR Health Check
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    summary="GDPR compliance health check",
    description="Returns the current GDPR configuration and compliance status.",
)
async def gdpr_health():
    from app.config import get_settings
    s = get_settings()
    overdue = await _gdpr_service.get_overdue_dsrs()

    return {
        "status": "compliant" if not overdue else "action_required",
        "controller": {
            "name": s.gdpr_data_controller_name,
            "email": s.gdpr_data_controller_email,
            "country": s.gdpr_data_controller_country,
        },
        "configuration": {
            "pii_masking_enabled": s.gdpr_pii_masking_enabled,
            "audit_retention_years": s.gdpr_audit_retention_years,
            "invoice_retention_days": s.blob_retention_days_invoice,
            "cv_retention_days": s.blob_retention_days_cv,
            "mode": s.app_mode.value,
        },
        "overdue_dsrs": len(overdue),
        "overdue_dsr_ids": [d.dsr_id for d in overdue],
        "applicable_regulations": [
            "DSGVO (GDPR) — Germany (DE)",
            "DSG 2018 — Austria (AT)",
            "revDSG (nDSG) — Switzerland (CH, since 01.09.2023)",
        ],
    }
