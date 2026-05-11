"""
app/database/models.py
=======================
SQLAlchemy ORM models.
Compatible with Azure SQL (MSSQL) and SQLite (local dev).
Tables: documents_invoice, documents_cv, consent_records,
        audit_logs, data_subject_requests, retention_schedule.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _uuid():
    return str(uuid.uuid4())


# ──────────────────────────────────────────────────────────────────────────────
# Invoice Documents
# ──────────────────────────────────────────────────────────────────────────────

class InvoiceDocument(Base):
    __tablename__ = "documents_invoice"

    id = Column(String(36), primary_key=True, default=_uuid)
    original_filename = Column(String(500), nullable=False)
    blob_url = Column(Text, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    language_detected = Column(String(10), nullable=True)
    country_detected = Column(String(5), nullable=True)

    # Vendor
    vendor_name = Column(String(500), nullable=True)
    vendor_name_confidence = Column(Float, default=0.0)
    vendor_tax_id = Column(String(100), nullable=True)
    vendor_iban = Column(String(100), nullable=True)

    # Invoice fields
    invoice_number = Column(String(200), nullable=True)
    invoice_number_confidence = Column(Float, default=0.0)
    invoice_date = Column(String(20), nullable=True)
    due_date = Column(String(20), nullable=True)
    payment_reference = Column(String(500), nullable=True)

    # Amounts
    currency = Column(String(10), default="EUR")
    subtotal_net = Column(Float, nullable=True)
    vat_amount = Column(Float, nullable=True)
    vat_rate = Column(Float, nullable=True)
    total_gross = Column(Float, nullable=True)
    total_gross_confidence = Column(Float, default=0.0)

    # Line items (stored as JSON)
    line_items_json = Column(JSON, nullable=True)

    # Quality
    overall_confidence = Column(Float, default=0.0)
    low_confidence_fields_json = Column(JSON, nullable=True)
    requires_manual_review = Column(Boolean, default=False)
    review_status = Column(String(50), default="auto_approved")
    review_notes = Column(Text, nullable=True)
    validation_errors_json = Column(JSON, nullable=True)
    validation_warnings_json = Column(JSON, nullable=True)

    # GDPR
    consent_id = Column(String(100), nullable=True)
    pii_masked = Column(Boolean, default=False)
    retention_until = Column(String(20), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    anonymised = Column(Boolean, default=False)

    # Full extraction result as JSON (for Power BI / export)
    raw_extraction_json = Column(JSON, nullable=True)


# ──────────────────────────────────────────────────────────────────────────────
# CV Documents
# ──────────────────────────────────────────────────────────────────────────────

class CVDocument(Base):
    __tablename__ = "documents_cv"

    id = Column(String(36), primary_key=True, default=_uuid)
    original_filename = Column(String(500), nullable=False)
    blob_url = Column(Text, nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    language_detected = Column(String(10), nullable=True)

    # Personal (PII — masked in GDPR context)
    full_name = Column(String(500), nullable=True)
    email = Column(String(500), nullable=True)
    phone = Column(String(100), nullable=True)
    location = Column(String(500), nullable=True)
    nationality = Column(String(200), nullable=True)

    # Professional
    current_title = Column(String(500), nullable=True)
    years_of_experience = Column(Float, nullable=True)
    target_role_category = Column(String(100), nullable=True)

    # Skills (stored as JSON arrays)
    technical_skills_json = Column(JSON, nullable=True)
    soft_skills_json = Column(JSON, nullable=True)
    all_skills_json = Column(JSON, nullable=True)

    # Languages
    german_proficiency = Column(String(20), nullable=True)
    languages_json = Column(JSON, nullable=True)

    # ATS
    ats_score = Column(Float, nullable=True)
    ats_details_json = Column(JSON, nullable=True)

    # DACH eligibility
    dach_eligibility = Column(String(50), nullable=True)
    dach_eligibility_note = Column(Text, nullable=True)

    # AI-generated fields
    recruiter_summary = Column(Text, nullable=True)
    improvement_suggestions_json = Column(JSON, nullable=True)

    # Quality
    overall_confidence = Column(Float, default=0.0)
    requires_manual_review = Column(Boolean, default=False)
    validation_warnings_json = Column(JSON, nullable=True)

    # GDPR
    consent_id = Column(String(100), nullable=True)
    pii_masked = Column(Boolean, default=False)
    retention_until = Column(String(20), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    anonymised = Column(Boolean, default=False)

    raw_extraction_json = Column(JSON, nullable=True)


# ──────────────────────────────────────────────────────────────────────────────
# GDPR — Consent Records
# ──────────────────────────────────────────────────────────────────────────────

class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id = Column(String(100), primary_key=True)   # consent_id
    document_id = Column(String(36), nullable=False)
    document_type = Column(String(20), nullable=False)
    data_subject_identifier = Column(String(200), nullable=False)   # pseudonymised
    legal_basis = Column(String(50), nullable=False)
    processing_purposes_json = Column(JSON, nullable=False)
    granted_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(30), default="granted")
    ip_address_hash = Column(String(200), nullable=True)
    consent_text_version = Column(String(20), default="1.0")
    controller_name = Column(String(500), nullable=False)
    controller_email = Column(String(500), nullable=False)


# ──────────────────────────────────────────────────────────────────────────────
# GDPR — Audit Log (immutable)
# ──────────────────────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(100), primary_key=True)   # audit_id
    timestamp = Column(DateTime(timezone=True), nullable=False)
    action = Column(String(100), nullable=False)
    document_id = Column(String(36), nullable=True)
    document_type = Column(String(20), nullable=True)
    actor_id = Column(String(200), nullable=False)
    actor_role = Column(String(100), nullable=False)
    ip_address_hash = Column(String(200), nullable=True)
    details_json = Column(JSON, nullable=True)
    outcome = Column(String(20), default="success")
    error_message = Column(Text, nullable=True)
    retention_years = Column(Integer, default=10)


# ──────────────────────────────────────────────────────────────────────────────
# GDPR — Data Subject Requests
# ──────────────────────────────────────────────────────────────────────────────

class DataSubjectRequestRecord(Base):
    __tablename__ = "data_subject_requests"

    id = Column(String(100), primary_key=True)   # dsr_id
    request_type = Column(String(50), nullable=False)
    data_subject_identifier = Column(String(200), nullable=False)
    received_at = Column(DateTime(timezone=True), nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(30), default="received")
    affected_document_ids_json = Column(JSON, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    response_notes = Column(Text, nullable=True)
    fulfilled_by = Column(String(200), nullable=True)
