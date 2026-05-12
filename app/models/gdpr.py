"""
app/models/gdpr.py
==================
GDPR / DSGVO / LPD models.
Covers: consent, audit logs, data subject requests (DSR),
retention policy, PII export, erasure (right to be forgotten).

Regulatory basis:
  DE — DSGVO (BDSG-neu)
  AT — DSG 2018
  CH — revDSG (nDSG, effective 01.09.2023)
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class LegalBasis(str, Enum):
    """GDPR Art. 6 legal bases for processing."""
    CONSENT = "consent"                         # Art. 6(1)(a)
    CONTRACT = "contract"                       # Art. 6(1)(b)
    LEGAL_OBLIGATION = "legal_obligation"       # Art. 6(1)(c)
    VITAL_INTERESTS = "vital_interests"         # Art. 6(1)(d)
    PUBLIC_TASK = "public_task"                 # Art. 6(1)(e)
    LEGITIMATE_INTERESTS = "legitimate_interests"  # Art. 6(1)(f)


class ConsentStatus(str, Enum):
    GRANTED = "granted"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class DataSubjectRequestType(str, Enum):
    """GDPR Chapter III data subject rights."""
    ACCESS = "access"                   # Art. 15 — Recht auf Auskunft
    RECTIFICATION = "rectification"    # Art. 16 — Recht auf Berichtigung
    ERASURE = "erasure"                 # Art. 17 — Recht auf Löschung
    RESTRICTION = "restriction"        # Art. 18 — Einschränkung der Verarbeitung
    PORTABILITY = "portability"        # Art. 20 — Datenübertragbarkeit
    OBJECTION = "objection"            # Art. 21 — Widerspruchsrecht


class DSRStatus(str, Enum):
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    OVERDUE = "overdue"


class AuditAction(str, Enum):
    UPLOAD = "upload"
    EXTRACT = "extract"
    VIEW = "view"
    EXPORT = "export"
    MASK_PII = "mask_pii"
    DELETE = "delete"
    CONSENT_GRANT = "consent_grant"
    CONSENT_WITHDRAW = "consent_withdraw"
    DSR_RECEIVED = "dsr_received"
    DSR_COMPLETED = "dsr_completed"
    RETENTION_APPLIED = "retention_applied"
    MANUAL_REVIEW = "manual_review"
    REVIEW_APPROVED = "review_approved"
    REVIEW_REJECTED = "review_rejected"


class DocumentType(str, Enum):
    INVOICE = "invoice"
    CV = "cv"


class RetentionRegime(str, Enum):
    """Legal retention regimes relevant in DACH."""
    HGB_DE = "hgb_de"          # HGB §257 — 6/10 years (DE)
    AO_DE = "ao_de"            # AO §147 — 10 years (DE, tax)
    UGB_AT = "ugb_at"          # UGB §212 (AT) — 7 years
    OR_CH = "or_ch"            # OR Art. 958f (CH) — 10 years
    GDPR_CONSENT = "gdpr_consent"   # Until consent withdrawn
    CUSTOM = "custom"


# ──────────────────────────────────────────────────────────────────────────────
# Consent
# ──────────────────────────────────────────────────────────────────────────────

class ConsentRecord(BaseModel):
    """GDPR Art. 7 — Conditions for consent."""
    consent_id: str
    document_id: str
    document_type: DocumentType
    data_subject_identifier: str = Field(
        ...,
        description="Hashed/pseudonymised identifier of the data subject"
    )
    legal_basis: LegalBasis
    processing_purposes: List[str] = Field(
        ..., description="e.g. ['invoice_processing', 'audit_compliance']"
    )
    granted_at: datetime
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    status: ConsentStatus = ConsentStatus.GRANTED
    ip_address_hash: Optional[str] = Field(
        None, description="SHA-256 of IP, not stored in clear"
    )
    consent_text_version: str = "1.0"
    controller_name: str
    controller_email: str

    class Config:
        json_schema_extra = {
            "example": {
                "consent_id": "cns-2024-abc123",
                "document_id": "cv-2024-001",
                "document_type": "cv",
                "data_subject_identifier": "sha256:abc...",
                "legal_basis": "consent",
                "processing_purposes": ["cv_processing", "recruiter_review"],
                "granted_at": "2024-03-15T10:00:00Z",
                "status": "granted"
            }
        }


# ──────────────────────────────────────────────────────────────────────────────
# Audit Log
# ──────────────────────────────────────────────────────────────────────────────

class AuditLogEntry(BaseModel):
    """
    Immutable audit log entry for all data processing operations.
    Must be retained for GDPR_AUDIT_RETENTION_YEARS (default 10).
    """
    audit_id: str
    timestamp: datetime
    action: AuditAction
    document_id: Optional[str] = None
    document_type: Optional[DocumentType] = None
    actor_id: str = Field(..., description="User/service identity (pseudonymised)")
    actor_role: str = Field(..., description="e.g. 'system', 'recruiter', 'admin'")
    ip_address_hash: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    outcome: str = "success"   # "success" | "failure"
    error_message: Optional[str] = None
    retention_years: int = 10


# ──────────────────────────────────────────────────────────────────────────────
# Data Subject Requests
# ──────────────────────────────────────────────────────────────────────────────

class DataSubjectRequest(BaseModel):
    """
    GDPR Chapter III — Data Subject Rights request.
    Must be fulfilled within 30 calendar days (Art. 12(3)).
    """
    dsr_id: str
    request_type: DataSubjectRequestType
    data_subject_identifier: str
    contact_email: Optional[str] = Field(
        None, description="[PII] For response delivery — not stored longer than needed"
    )
    received_at: datetime
    deadline: datetime = Field(
        ..., description="Art. 12(3): 30 days from receipt. Extendable to 90 days."
    )
    status: DSRStatus = DSRStatus.RECEIVED
    affected_document_ids: List[str] = Field(default_factory=list)
    completed_at: Optional[datetime] = None
    response_notes: Optional[str] = None
    fulfilled_by: Optional[str] = None


class DataExportPackage(BaseModel):
    """
    GDPR Art. 20 — Data Portability export package.
    Machine-readable format (JSON).
    """
    export_id: str
    dsr_id: str
    created_at: datetime
    expires_at: datetime = Field(..., description="Secure link expires after 7 days")
    download_url: Optional[str] = None
    documents_included: List[str] = Field(default_factory=list)
    format: str = "JSON"
    encrypted: bool = True
    checksum_sha256: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Retention
# ──────────────────────────────────────────────────────────────────────────────

class RetentionPolicy(BaseModel):
    """Per-document-type retention policy."""
    document_type: DocumentType
    regime: RetentionRegime
    retention_days: int
    legal_reference: str = Field(..., description="e.g. 'HGB §257 Abs. 1 Nr. 4'")
    auto_delete_enabled: bool = True
    country: str = "DE"
    notes: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# PII Masking
# ──────────────────────────────────────────────────────────────────────────────

class PIIMaskingReport(BaseModel):
    """Report of PII fields that were masked/pseudonymised."""
    document_id: str
    document_type: DocumentType
    masked_at: datetime
    fields_masked: List[str]
    masking_method: str = Field(
        "pseudonymisation",
        description="'pseudonymisation' | 'anonymisation' | 'encryption'"
    )
    reversible: bool = Field(
        True,
        description="True=pseudonymisation (reversible with key), False=anonymisation"
    )
    masked_by: str


# ──────────────────────────────────────────────────────────────────────────────
# Request/Response models for API
# ──────────────────────────────────────────────────────────────────────────────

class ConsentGrantRequest(BaseModel):
    document_id: str
    document_type: DocumentType
    data_subject_identifier: str
    legal_basis: LegalBasis = LegalBasis.CONSENT
    processing_purposes: List[str]
    consent_text_version: str = "1.0"


class DSRSubmitRequest(BaseModel):
    request_type: DataSubjectRequestType
    data_subject_identifier: str
    contact_email: Optional[str] = None
    affected_document_ids: Optional[List[str]] = None


class DSRSubmitResponse(BaseModel):
    dsr_id: str
    request_type: DataSubjectRequestType
    deadline: str
    message: str
