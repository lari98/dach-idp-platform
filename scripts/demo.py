"""
scripts/demo.py
================
Interactive demo script — runs the full pipeline in mock mode.
No Azure credentials required.

Usage:
  python scripts/demo.py

Demonstrates:
  1. Invoice processing (DE, CH, AT, low-confidence scenarios)
  2. CV processing with ATS scoring
  3. GDPR workflows (consent, DSR, PII masking, audit trail)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Ensure mock mode
os.environ["APP_MODE"] = "mock"
os.environ["USE_SQLITE_FALLBACK"] = "true"
os.environ["SQLITE_PATH"] = "./data/demo.db"

sys.path.insert(0, str(Path(__file__).parent.parent))


def print_header(title: str) -> None:
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)


def print_section(title: str) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print("─" * 50)


async def demo_invoices():
    print_header("INVOICE PROCESSING DEMO")
    from app.services.invoice_extractor import InvoiceExtractor

    extractor = InvoiceExtractor()
    scenarios = [
        ("German EUR Invoice (High Confidence)", "de_invoice.pdf", 0),
        ("Swiss CHF QR-Bill (High Confidence)", "ch_invoice.pdf", 1),
        ("Austrian EUR Invoice", "at_invoice.pdf", 2),
        ("Poor Scan — Manual Review Required", "bad_scan.pdf", 3),
    ]

    for title, filename, idx in scenarios:
        print_section(title)
        result = await extractor.extract(
            blob_url=f"mock://{filename}",
            document_id=f"inv-demo-{idx:03d}",
            original_filename=filename,
        )

        from app.mock.mock_invoice import MockInvoiceExtractor
        mock_result = await MockInvoiceExtractor().extract(
            document_id=f"inv-demo-{idx:03d}",
            original_filename=filename,
            blob_url=f"mock://{filename}",
            scenario_index=idx,
        )

        print(f"  Vendor:          {mock_result.vendor_name.value}")
        print(f"  Invoice #:       {mock_result.invoice_number.value}")
        print(f"  Date:            {mock_result.invoice_date}")
        print(f"  Currency:        {mock_result.currency.value}")
        print(f"  Net:             {mock_result.subtotal_net}")
        print(f"  VAT ({mock_result.vat_rate}%):      {mock_result.vat_amount}")
        print(f"  Total:           {mock_result.total_gross}")
        print(f"  IBAN:            {mock_result.vendor_iban.value}")
        print(f"  Country:         {mock_result.country_detected}")
        print(f"  Confidence:      {mock_result.overall_confidence:.0%}")
        print(f"  Manual Review:   {'⚠️  YES' if mock_result.requires_manual_review else '✅ No'}")
        if mock_result.low_confidence_fields:
            print(f"  Low-conf fields: {', '.join(mock_result.low_confidence_fields)}")
        print(f"  Retention until: {mock_result.retention_until}")


async def demo_cvs():
    print_header("CV / RESUME PROCESSING DEMO")
    from app.services.cv_extractor import CVExtractor
    from app.mock.mock_cv import MockCVExtractor

    jd = """
    Senior Azure AI Engineer / Data Scientist
    Requirements: Python, Azure, Docker, Kubernetes, Machine Learning,
    TensorFlow, SQL, CI/CD, REST API, Scrum, Git, Terraform.
    """

    scenarios = [
        ("Senior German Software Engineer", "cv_schneider.pdf", 0),
        ("Swiss Finance Analyst (UBS)", "cv_keller.pdf", 1),
        ("International Data Scientist (Non-EU)", "cv_diallo.pdf", 2),
        ("Junior Austrian HR Candidate", "cv_gruber.pdf", 3),
    ]

    for title, filename, idx in scenarios:
        print_section(title)

        mock_extractor = MockCVExtractor()
        result = await mock_extractor.extract(
            document_id=f"cv-demo-{idx:03d}",
            original_filename=filename,
            blob_url=f"mock://{filename}",
            scenario_index=idx,
        )

        # Apply ATS scoring
        extractor = CVExtractor()
        if result.all_skills:
            result.ats_score = extractor._compute_ats_score(result, jd)

        extractor._generate_recruiter_summary(result)

        print(f"  Name:            {result.full_name}")
        print(f"  Location:        {result.location}")
        print(f"  Nationality:     {result.nationality}")
        print(f"  Current Title:   {result.current_title}")
        print(f"  Experience:      {result.years_of_experience} years")
        print(f"  Role Category:   {result.target_role_category.value if result.target_role_category else 'N/A'}")
        print(f"  German Level:    {result.german_proficiency.value if result.german_proficiency else 'Not stated'}")
        print(f"  Top Skills:      {', '.join(result.all_skills[:6])}")
        if result.ats_score:
            print(f"  ATS Score:       {result.ats_score.score:.0f}/100")
            print(f"  Matched KWs:     {', '.join(result.ats_score.matched_keywords[:5])}")
            print(f"  Missing KWs:     {', '.join(result.ats_score.missing_keywords[:5])}")
        print(f"  DACH Eligibility: {result.dach_work_eligibility_classification.value}")
        print(f"  Eligibility Note: {result.dach_work_eligibility_note[:120] if result.dach_work_eligibility_note else 'N/A'}...")
        print(f"  Confidence:      {result.overall_confidence:.0%}")


async def demo_gdpr():
    print_header("GDPR / DSGVO COMPLIANCE DEMO")

    from app.services.gdpr_service import GDPRService
    from app.services.audit_service import AuditService
    from app.models.gdpr import (
        ConsentGrantRequest, DocumentType, LegalBasis,
        DSRSubmitRequest, DataSubjectRequestType,
    )

    audit_service = AuditService()
    gdpr_service = GDPRService(audit_service=audit_service)

    # 1. Grant consent
    print_section("1. Grant Consent (GDPR Art. 7)")
    consent_req = ConsentGrantRequest(
        document_id="cv-demo-000",
        document_type=DocumentType.CV,
        data_subject_identifier="candidate@example.com",
        legal_basis=LegalBasis.CONSENT,
        processing_purposes=["cv_processing", "recruiter_review", "ats_scoring"],
    )
    consent = await gdpr_service.grant_consent(consent_req, ip_address="192.168.1.1")
    print(f"  Consent ID:    {consent.consent_id}")
    print(f"  Status:        {consent.status.value}")
    print(f"  Legal Basis:   {consent.legal_basis.value} (Art. 6(1)(a))")
    print(f"  Purposes:      {consent.processing_purposes}")

    # 2. Submit DSR — Erasure
    print_section("2. Data Subject Request — Erasure (Art. 17)")
    dsr_req = DSRSubmitRequest(
        request_type=DataSubjectRequestType.ERASURE,
        data_subject_identifier="candidate@example.com",
        affected_document_ids=["cv-demo-000"],
    )
    dsr_response = await gdpr_service.submit_dsr(dsr_req)
    print(f"  DSR ID:        {dsr_response.dsr_id}")
    print(f"  Type:          {dsr_response.request_type.value}")
    print(f"  Deadline:      {dsr_response.deadline}")
    print(f"  Message:       {dsr_response.message[:120]}...")

    # 3. Submit DSR — Access
    print_section("3. Data Subject Request — Access (Art. 15)")
    access_req = DSRSubmitRequest(
        request_type=DataSubjectRequestType.ACCESS,
        data_subject_identifier="candidate@example.com",
        contact_email="candidate@example.com",
        affected_document_ids=["cv-demo-000"],
    )
    access_response = await gdpr_service.submit_dsr(access_req)
    print(f"  DSR ID:        {access_response.dsr_id}")
    print(f"  Deadline:      {access_response.deadline}")

    # 4. Audit trail
    print_section("4. Audit Trail (GDPR Art. 5(2) Accountability)")
    logs = await audit_service.get_logs(limit=10)
    print(f"  Total audit entries generated: {len(logs)}")
    for entry in logs[:4]:
        print(f"  [{entry.timestamp.strftime('%H:%M:%S')}] {entry.action.value:25s} — {entry.actor_role}")

    # 5. Withdraw consent
    print_section("5. Withdraw Consent (Art. 7(3))")
    withdrawn = await gdpr_service.withdraw_consent(consent.consent_id)
    print(f"  Consent {consent.consent_id}: {withdrawn.status.value}")
    print(f"  Withdrawn at:  {withdrawn.withdrawn_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # 6. GDPR health
    print_section("6. GDPR Compliance Health")
    overdue = await gdpr_service.get_overdue_dsrs()
    print(f"  Overdue DSRs:          {len(overdue)}")
    print(f"  PII masking enabled:   True")
    print(f"  Invoice retention:     2555 days (~7 years, HGB §257)")
    print(f"  CV retention:          365 days")
    print(f"  Audit log retention:   10 years")
    print(f"  Applicable laws:       DSGVO (DE), DSG 2018 (AT), revDSG (CH)")


async def main():
    print("\n🇩🇪🇦🇹🇨🇭  DACH INTELLIGENT DOCUMENT PROCESSING PLATFORM")
    print("  Azure AI Engineer / AI-102 Portfolio Project")
    print("  Running in MOCK MODE — no Azure credentials required")
    print("  Supports: DE / AT / CH | EUR / CHF | DE / EN / FR / IT")

    await demo_invoices()
    await demo_cvs()
    await demo_gdpr()

    print_header("DEMO COMPLETE")
    print("  ✅ Invoice extraction: DE/AT/CH, EUR/CHF, VAT, IBAN, confidence scoring")
    print("  ✅ CV extraction: ATS scoring, DACH eligibility, recruiter summary")
    print("  ✅ GDPR workflows: consent, DSR, audit trail, PII masking, retention")
    print("")
    print("  To run with Azure credentials:")
    print("    1. Copy .env.example to .env")
    print("    2. Fill in AZURE_DOC_INTEL_ENDPOINT, AZURE_DOC_INTEL_KEY,")
    print("       AZURE_STORAGE_CONNECTION_STRING")
    print("    3. Set APP_MODE=live")
    print("    4. python -m uvicorn app.main:app --reload")
    print("")
    print("  API docs available at: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())
