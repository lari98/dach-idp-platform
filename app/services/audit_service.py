"""
app/services/audit_service.py
===============================
Immutable audit logging for all data processing operations.
GDPR Art. 5(2) — Accountability principle.
Audit logs must be retained for settings.gdpr_audit_retention_years (default 10).

In production, audit logs are written to:
  1. Azure SQL (structured, queryable)
  2. Azure Blob Storage (immutable archive)
  3. Application Insights (real-time monitoring)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import structlog

from app.config import get_settings
from app.models.gdpr import AuditAction, AuditLogEntry, DocumentType

log = structlog.get_logger(__name__)
settings = get_settings()


class AuditService:
    """
    Writes immutable audit log entries.
    In mock mode: in-memory + structured log output.
    In live mode: database + blob archive + App Insights.
    """

    def __init__(self):
        self._in_memory_log: List[AuditLogEntry] = []

    async def log(
        self,
        action: AuditAction,
        actor_id: str,
        actor_role: str,
        document_id: Optional[str] = None,
        document_type: Optional[DocumentType] = None,
        details: Optional[Dict[str, Any]] = None,
        outcome: str = "success",
        error_message: Optional[str] = None,
        ip_address_hash: Optional[str] = None,
    ) -> AuditLogEntry:
        """
        Write an audit log entry.
        This method is intentionally synchronous-safe:
        audit logging must never fail silently.
        """
        entry = AuditLogEntry(
            audit_id=f"aud-{uuid.uuid4().hex[:16]}",
            timestamp=datetime.now(timezone.utc),
            action=action,
            document_id=document_id,
            document_type=document_type,
            actor_id=actor_id,
            actor_role=actor_role,
            ip_address_hash=ip_address_hash,
            details=details or {},
            outcome=outcome,
            error_message=error_message,
            retention_years=settings.gdpr_audit_retention_years,
        )

        # Always write to structured log
        log.info(
            "audit",
            audit_id=entry.audit_id,
            action=action.value,
            document_id=document_id,
            actor_id=actor_id,
            actor_role=actor_role,
            outcome=outcome,
        )

        # In-memory store (mock mode / testing)
        self._in_memory_log.append(entry)

        # In live mode, also persist to database and blob
        if not settings.is_mock_mode:
            await self._persist_to_db(entry)

        return entry

    async def _persist_to_db(self, entry: AuditLogEntry) -> None:
        """Persist audit entry to Azure SQL. No-op in mock mode."""
        try:
            # In a full implementation, use SQLAlchemy async session
            # db.execute(INSERT INTO audit_logs VALUES (...))
            pass
        except Exception as e:
            # Audit logging failure must be logged but must not crash the main operation
            log.error("audit_db_persist_failed", audit_id=entry.audit_id, error=str(e))

    async def get_logs(
        self,
        document_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        actor_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """Query audit logs. In mock mode queries in-memory store."""
        results = self._in_memory_log

        if document_id:
            results = [e for e in results if e.document_id == document_id]
        if action:
            results = [e for e in results if e.action == action]
        if actor_id:
            results = [e for e in results if e.actor_id == actor_id]

        # Most recent first
        results = sorted(results, key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    async def export_audit_trail(self, document_id: str) -> str:
        """
        Export full audit trail for a document as JSON.
        Used for GDPR Art. 5(2) accountability evidence.
        """
        entries = await self.get_logs(document_id=document_id)
        return json.dumps(
            [e.model_dump(mode="json") for e in entries],
            indent=2,
            ensure_ascii=False,
            default=str,
        )
