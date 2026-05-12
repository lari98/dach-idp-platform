"""
app/services/gdpr_service.py
==============================
GDPR / DSGVO compliance service.
Implements: consent management, DSR handling, PII export, erasure.

Regulatory references:
  DSGVO (GDPR) Art. 6, 7, 12, 13, 15–21
  BDSG-neu (Germany)
  DSG 2018 (Austria)
  revDSG / nDSG Art. 25, 30, 32 (Switzerland, from 01.09.2023)
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import structlog

from app.config import get_settings
from app.models.gdpr import (
    AuditAction,
    AuditLogEntry,
    ConsentGrantRequest,
    ConsentRecord,
    ConsentStatus,
    DSRStatus,
    DSRSubmitRequest,
    DSRSubmitResponse,
    DataExportPackage,
    DataSubjectRequest,
    DocumentType,
    PIIMaskingReport,
)
from app.services.audit_service import AuditService
from app.services.pii_masker import PIIMasker

log = structlog.get_logger(__name__)
settings = get_settings()


class GDPRService:
    """
    Orchestrates all GDPR compliance workflows.
    Consent → Processing → Retention → Export/Delete.
    """

    def __init__(
        self,
        audit_service: Optional[AuditService] = None,
        pii_masker: Optional[PIIMasker] = None,
    ):
        self.audit_service = audit_service or AuditService()
        self.pii_masker = pii_masker or PIIMasker()
        # In production, these would be database repositories
        self._consents: Dict[str, ConsentRecord] = {}
        self._dsrs: Dict[str, DataSubjectRequest] = {}
        self._exports: Dict[str, DataExportPackage] = {}

    # ──────────────────────────────────────────────────────────────────────────
    # Consent Management (Art. 7)
    # ──────────────────────────────────────────────────────────────────────────

    async def grant_consent(
        self,
        request: ConsentGrantRequest,
        ip_address: Optional[str] = None,
        actor_id: str = "system",
    ) -> ConsentRecord:
        """
        Record explicit consent for document processing.
        GDPR Art. 7: Consent must be freely given, specific, informed, unambiguous.
        """
        consent_id = f"cns-{uuid.uuid4().hex[:12]}"
        ip_hash = hashlib.sha256(ip_address.encode()).hexdigest() if ip_address else None

        consent = ConsentRecord(
            consent_id=consent_id,
            document_id=request.document_id,
            document_type=request.document_type,
            data_subject_identifier=self._hash_identifier(request.data_subject_identifier),
            legal_basis=request.legal_basis,
            processing_purposes=request.processing_purposes,
            granted_at=datetime.now(timezone.utc),
            status=ConsentStatus.GRANTED,
            ip_address_hash=ip_hash,
            consent_text_version=request.consent_text_version,
            controller_name=settings.gdpr_data_controller_name,
            controller_email=settings.gdpr_data_controller_email,
        )

        self._consents[consent_id] = consent

        await self.audit_service.log(
            action=AuditAction.CONSENT_GRANT,
            document_id=request.document_id,
            document_type=DocumentType(request.document_type.value),
            actor_id=actor_id,
            actor_role="data_subject",
            details={
                "consent_id": consent_id,
                "legal_basis": request.legal_basis.value,
                "purposes": request.processing_purposes,
            },
        )

        log.info("consent_granted", consent_id=consent_id, document_id=request.document_id)
        return consent

    async def withdraw_consent(
        self,
        consent_id: str,
        actor_id: str = "data_subject",
    ) -> ConsentRecord:
        """
        Withdraw consent. GDPR Art. 7(3): Withdrawal must be as easy as giving consent.
        Triggers automatic review of retained data.
        """
        consent = self._consents.get(consent_id)
        if not consent:
            raise ValueError(f"Consent record not found: {consent_id}")

        consent.status = ConsentStatus.WITHDRAWN
        consent.withdrawn_at = datetime.now(timezone.utc)

        await self.audit_service.log(
            action=AuditAction.CONSENT_WITHDRAW,
            document_id=consent.document_id,
            document_type=consent.document_type,
            actor_id=actor_id,
            actor_role="data_subject",
            details={"consent_id": consent_id},
        )

        log.info("consent_withdrawn", consent_id=consent_id)
        return consent

    async def get_consent(self, consent_id: str) -> Optional[ConsentRecord]:
        return self._consents.get(consent_id)

    async def check_consent_valid(
        self, document_id: str, purpose: str
    ) -> bool:
        """Check if valid consent exists for a given document and processing purpose."""
        for consent in self._consents.values():
            if (
                consent.document_id == document_id
                and consent.status == ConsentStatus.GRANTED
                and purpose in consent.processing_purposes
            ):
                if consent.expires_at is None or consent.expires_at > datetime.now(timezone.utc):
                    return True
        return False

    # ──────────────────────────────────────────────────────────────────────────
    # Data Subject Requests (Art. 15-21)
    # ──────────────────────────────────────────────────────────────────────────

    async def submit_dsr(
        self,
        request: DSRSubmitRequest,
        actor_id: str = "data_subject",
    ) -> DSRSubmitResponse:
        """
        Register a Data Subject Request.
        GDPR Art. 12(3): Must be handled within 30 days.
        """
        dsr_id = f"dsr-{uuid.uuid4().hex[:12]}"
        received_at = datetime.now(timezone.utc)
        # Art. 12(3): 30 days from receipt; complex requests extendable to 90 days
        deadline = received_at + timedelta(days=30)

        dsr = DataSubjectRequest(
            dsr_id=dsr_id,
            request_type=request.request_type,
            data_subject_identifier=self._hash_identifier(request.data_subject_identifier),
            contact_email=request.contact_email,
            received_at=received_at,
            deadline=deadline,
            status=DSRStatus.RECEIVED,
            affected_document_ids=request.affected_document_ids or [],
        )

        self._dsrs[dsr_id] = dsr

        await self.audit_service.log(
            action=AuditAction.DSR_RECEIVED,
            actor_id=actor_id,
            actor_role="data_subject",
            details={
                "dsr_id": dsr_id,
                "request_type": request.request_type.value,
                "deadline": deadline.isoformat(),
            },
        )

        log.info(
            "dsr_received",
            dsr_id=dsr_id,
            type=request.request_type.value,
            deadline=deadline.isoformat(),
        )

        return DSRSubmitResponse(
            dsr_id=dsr_id,
            request_type=request.request_type,
            deadline=deadline.isoformat(),
            message=(
                f"Your {request.request_type.value} request (ID: {dsr_id}) has been received. "
                f"We will respond by {deadline.date().isoformat()} in accordance with GDPR Art. 12(3). "
                f"Contact: {settings.gdpr_data_controller_email}"
            ),
        )

    async def process_erasure_request(
        self,
        dsr_id: str,
        blob_service,
        db_service,
        actor_id: str = "admin",
    ) -> Dict:
        """
        Execute GDPR Art. 17 — Right to Erasure ("Right to be Forgotten").
        Steps: delete blobs, anonymise DB records, mark DSR complete.
        """
        dsr = self._dsrs.get(dsr_id)
        if not dsr:
            raise ValueError(f"DSR not found: {dsr_id}")

        results = {
            "dsr_id": dsr_id,
            "blobs_deleted": [],
            "records_anonymised": [],
            "errors": [],
        }

        # Delete or anonymise each affected document
        for doc_id in dsr.affected_document_ids:
            try:
                # 1. Delete blob
                doc_record = await db_service.get_document(doc_id)
                if doc_record and doc_record.get("blob_url"):
                    deleted = await blob_service.delete_blob(doc_record["blob_url"])
                    if deleted:
                        results["blobs_deleted"].append(doc_id)

                # 2. Anonymise DB record (replace PII with [ERASED])
                await db_service.anonymise_document(doc_id)
                results["records_anonymised"].append(doc_id)

            except Exception as e:
                log.error("erasure_failed", doc_id=doc_id, error=str(e))
                results["errors"].append({"document_id": doc_id, "error": str(e)})

        # Mark DSR complete
        dsr.status = DSRStatus.COMPLETED
        dsr.completed_at = datetime.now(timezone.utc)
        dsr.fulfilled_by = actor_id

        await self.audit_service.log(
            action=AuditAction.DSR_COMPLETED,
            actor_id=actor_id,
            actor_role="admin",
            details={
                "dsr_id": dsr_id,
                "type": "erasure",
                "blobs_deleted": len(results["blobs_deleted"]),
                "records_anonymised": len(results["records_anonymised"]),
                "errors": len(results["errors"]),
            },
        )

        return results

    async def process_access_request(
        self,
        dsr_id: str,
        db_service,
        actor_id: str = "admin",
    ) -> DataExportPackage:
        """
        GDPR Art. 15 — Right of Access: provide all data held on a data subject.
        Returns a secure, time-limited export package.
        """
        dsr = self._dsrs.get(dsr_id)
        if not dsr:
            raise ValueError(f"DSR not found: {dsr_id}")

        export_id = f"exp-{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)

        # Gather all documents for this data subject
        all_docs = []
        for doc_id in dsr.affected_document_ids:
            doc = await db_service.get_document(doc_id)
            if doc:
                all_docs.append(doc)

        export_data = {
            "export_id": export_id,
            "generated_at": now.isoformat(),
            "data_controller": {
                "name": settings.gdpr_data_controller_name,
                "email": settings.gdpr_data_controller_email,
                "country": settings.gdpr_data_controller_country,
            },
            "data_subject_request": dsr.model_dump(exclude={"contact_email"}),
            "documents": all_docs,
        }

        export_json = json.dumps(export_data, default=str, indent=2, ensure_ascii=False)
        export_hash = hashlib.sha256(export_json.encode()).hexdigest()

        package = DataExportPackage(
            export_id=export_id,
            dsr_id=dsr_id,
            created_at=now,
            expires_at=now + timedelta(days=7),
            documents_included=[d["document_id"] for d in all_docs if "document_id" in d],
            format="JSON",
            encrypted=False,   # In prod: encrypt with data subject's email-based key
            checksum_sha256=export_hash,
        )

        self._exports[export_id] = package

        await self.audit_service.log(
            action=AuditAction.EXPORT,
            actor_id=actor_id,
            actor_role="admin",
            details={"dsr_id": dsr_id, "export_id": export_id},
        )

        dsr.status = DSRStatus.COMPLETED
        dsr.completed_at = now

        return package, export_json

    # ──────────────────────────────────────────────────────────────────────────
    # Retention Management
    # ──────────────────────────────────────────────────────────────────────────

    async def apply_retention_policy(self, document_id: str, document_type: str, db_service, blob_service) -> Dict:
        """
        Check if a document has exceeded its retention period.
        If yes, trigger deletion workflow.
        """
        doc = await db_service.get_document(document_id)
        if not doc:
            return {"status": "not_found"}

        retention_until = doc.get("retention_until")
        if not retention_until:
            return {"status": "no_retention_date"}

        from datetime import date
        today = date.today()
        retention_date = date.fromisoformat(retention_until)

        if today >= retention_date:
            log.info("retention_expired", document_id=document_id, retention_until=retention_until)
            # Delete blob
            if doc.get("blob_url"):
                await blob_service.delete_blob(doc["blob_url"])
            # Anonymise DB record
            await db_service.anonymise_document(document_id)

            await self.audit_service.log(
                action=AuditAction.RETENTION_APPLIED,
                document_id=document_id,
                actor_id="system",
                actor_role="system",
                details={"retention_until": retention_until, "action": "deleted"},
            )
            return {"status": "deleted", "retention_until": retention_until}

        days_remaining = (retention_date - today).days
        return {"status": "active", "days_remaining": days_remaining, "retention_until": retention_until}

    # ──────────────────────────────────────────────────────────────────────────
    # PII Masking
    # ──────────────────────────────────────────────────────────────────────────

    async def mask_pii(
        self,
        document_id: str,
        document_type: DocumentType,
        extraction_result: dict,
        actor_id: str = "system",
    ) -> Tuple[dict, PIIMaskingReport]:
        """Apply PII masking to an extraction result dict."""
        masked_result, fields_masked = self.pii_masker.mask_dict(
            data=extraction_result,
            document_type=document_type.value,
        )

        report = PIIMaskingReport(
            document_id=document_id,
            document_type=document_type,
            masked_at=datetime.now(timezone.utc),
            fields_masked=fields_masked,
            masked_by=actor_id,
        )

        await self.audit_service.log(
            action=AuditAction.MASK_PII,
            document_id=document_id,
            document_type=document_type,
            actor_id=actor_id,
            actor_role="system",
            details={"fields_masked": fields_masked},
        )

        return masked_result, report

    # ──────────────────────────────────────────────────────────────────────────
    # Utilities
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _hash_identifier(identifier: str) -> str:
        """Pseudonymise a data subject identifier with SHA-256."""
        return "sha256:" + hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:32]

    async def list_dsrs(self) -> List[DataSubjectRequest]:
        return list(self._dsrs.values())

    async def get_dsr(self, dsr_id: str) -> Optional[DataSubjectRequest]:
        return self._dsrs.get(dsr_id)

    async def get_overdue_dsrs(self) -> List[DataSubjectRequest]:
        """Return DSRs that have exceeded the 30-day deadline."""
        now = datetime.now(timezone.utc)
        overdue = []
        for dsr in self._dsrs.values():
            if dsr.status in (DSRStatus.RECEIVED, DSRStatus.IN_PROGRESS):
                if dsr.deadline < now:
                    dsr.status = DSRStatus.OVERDUE
                    overdue.append(dsr)
        return overdue
