"""
app/database/models.py  [v2.0.0]
==================================
SQLAlchemy ORM models.
Compatible with Azure SQL (MSSQL) and SQLite (local dev / mock mode).

v2.0.0 additions to CVDocument:
  - ats_match_score          (Float)
  - matched_keywords_json    (JSON)
  - missing_keywords_json    (JSON)
  - improvement_suggestions_json (JSON)
  - dach_work_eligibility_notes (Text)
  - manual_review_required   (Boolean)
  - risk_flags_json          (JSON)
  - candidate_country        (String)
  - candidate_language       (String)
  - review_queue_priority    (Integer)
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
# CV Documents  [v2.0.0 — extended with dashboard/recruiter fields]
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

    # Geographic / language dimensions (for dashboards)
    candidate_country = Column(String(5), nullable=True,
                               comment="ISO 3166-1 alpha-2: DE, AT, CH, FR, IT, OTHER")
    candidate_language = Column(String(10), nullable=True,
                                comment="BCP-47 primary language: de, en, fr, it")

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

    # ── v2.0.0 ATS fields ────────────────────────────────────────────────────
    ats_score = Column(Float, nullable=True,
                       comment="Overall ATS score 0-100 (v1: ats_score)")
    ats_match_score = Column(Float, nullable=True,
                             comment="v2: explicit match score alias, 0-100")
    ats_details_json = Column(JSON, nullable=True)
    matched_keywords_json = Column(JSON, nullable=True,
                                   comment="List of keywords found in both CV and JD")
    missing_keywords_json = Column(JSON, nullable=True,
                                   comment="Keywords in JD not found in CV")

    # ── v2.0.0 DACH eligibility ───────────────────────────────────────────────
    dach_eligibility = Column(String(50), nullable=True)
    dach_work_eligibility_notes = Column(Text, nullable=True,
                                         comment="v2: explicit eligibility note field (informational only)")

    # ── v2.0.0 Recruiter / review fields ─────────────────────────────────────
    recruiter_summary = Column(Text, nullable=True)
    improvement_suggestions_json = Column(JSON, nullable=True,
                                          comment="v2: list of actionable improvement suggestions")
    improvement_suggestion_count = Column(Integer, default=0,
                                          comment="v2: count for dashboard filtering")

    # ── v2.0.0 Review queue / risk ────────────────────────────────────────────
    manual_review_required = Column(Boolean, default=False,
                                    comment="v2: explicit flag (alias for requires_manual_review)")
    review_queue_priority = Column(Integer, default=0,
                                   comment="v2: 0=low,1=medium,2=high priority in review queue")
    risk_flags_json = Column(JSON, nullable=True,
                              comment="v2: list of risk flag strings, e.g. ['missing_iban','low_confidence']")
    missing_work_eligibility = Column(Boolean, default=False,
                                      comment="v2: True if dach_eligibility is UNKNOWN")

    # Quality (existing)
    overall_confidence = Column(Float, default=0.0)
    requires_manual_review = Column(Boolean, default=False)
    validation_warnings_json = Column(JSON, nullable=True)

    # Processing status
    processing_status = Column(String(30), default="complete",
                                comment="pending | processing | complete | failed")

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

    id = Column(String(100), primary_key=True)
    document_id = Column(String(36), nullable=False)
    document_type = Column(String(20), nullable=False)
    data_subject_identifier = Column(String(200), nullable=False)
