# Architecture — DACH IDP Platform

## Overview

The DACH Intelligent Document Processing Platform is a cloud-native, event-driven
document processing system for invoices and CVs/resumes, purpose-built for the
DACH region (Germany, Austria, Switzerland). It is designed to align with the
**Azure AI Engineer (AI-102)** certification skill domain.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        DACH IDP Platform — Azure Architecture                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   CLIENT / RECRUITER / AP TEAM                                               │
│        │  HTTPS (PDF Upload)                                                  │
│        ▼                                                                     │
│   ┌──────────────────────┐                                                   │
│   │  Azure App Service   │  FastAPI (Python 3.11)                            │
│   │  (Web API)           │  Managed Identity                                 │
│   └──────┬───────────────┘                                                   │
│          │                                                                   │
│   ┌──────▼──────────┐   ┌───────────────────────────────┐                  │
│   │ Azure Blob      │   │  Azure AI Document Intelligence│                  │
│   │ Storage         │──▶│  (prebuilt-invoice / custom)   │                  │
│   │ (invoices/cvs)  │   │  Language: DE, EN, FR, IT      │                  │
│   └──────┬──────────┘   └───────────────┬───────────────┘                  │
│          │                              │ Structured JSON                   │
│          │                      ┌───────▼────────────────────┐              │
│          │                      │  Extraction Engine          │              │
│          │                      │  - Invoice Extractor        │              │
│          │                      │  - CV Extractor             │              │
│          │                      │  - Confidence Scoring       │              │
│          │                      │  - IBAN/VAT Validation      │              │
│          │                      │  - ATS Scoring              │              │
│          │                      │  - GDPR Post-processing     │              │
│          │                      └───────┬────────────────────┘              │
│          │                              │                                   │
│   ┌──────▼──────────────────────────────▼───────┐                          │
│   │              Azure SQL Database              │                          │
│   │  documents_invoice  │  documents_cv          │                          │
│   │  consent_records    │  audit_logs            │                          │
│   │  data_subject_requests                       │                          │
│   └──────────────────────────┬───────────────────┘                          │
│                              │                                               │
│                    ┌─────────▼──────────┐                                   │
│                    │  Power BI Service  │  Dashboards:                      │
│                    │  (Push Dataset)    │  - Invoice Analytics               │
│                    │                    │  - CV Pipeline                    │
│                    │                    │  - GDPR Compliance                │
│                    └────────────────────┘                                   │
│                                                                              │
│   CROSS-CUTTING SERVICES                                                     │
│   ├── Azure Key Vault (secrets, encryption keys)                            │
│   ├── Application Insights (telemetry, performance)                         │
│   └── GitHub Actions CI (lint → test → docker build)                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### API Layer (FastAPI)
- **app/main.py** — Application entry point, middleware, lifespan
- **app/api/invoices.py** — Invoice CRUD + review workflow
- **app/api/cvs.py** — CV CRUD + ATS scoring + PII masking
- **app/api/gdpr.py** — Consent, DSR, audit, PII masking, retention

### Extraction Services
- **InvoiceExtractor** — Routes to Azure or mock; confidence flagging; DACH validation
- **CVExtractor** — Extracts structured CV data; ATS scoring; DACH eligibility; recruiter summary
- **BlobStorageService** — Azure Blob (live) or local filesystem (mock)

### GDPR Services
- **GDPRService** — Consent lifecycle, DSR handling, erasure, access export
- **AuditService** — Immutable structured log for all operations
- **PIIMasker** — Pseudonymisation / redaction of PII fields and free text

### Data Layer
- **SQLAlchemy ORM** — Async, compatible with Azure SQL + SQLite
- Tables: `documents_invoice`, `documents_cv`, `consent_records`, `audit_logs`, `data_subject_requests`

### Infrastructure (Bicep)
- Azure Document Intelligence (F0 dev / S0 prod)
- Azure Blob Storage (LRS dev / GRS prod)
- Azure SQL Database (Basic dev / S2 prod)
- Azure App Service (B1 dev / P1v3 prod)
- Azure Key Vault + Application Insights

---

## Data Flow — Invoice

```
PDF Upload
  │
  ▼
BlobStorageService.upload_document()
  │ Returns blob_url
  ▼
InvoiceExtractor.extract(blob_url)
  │
  ├─ [MOCK] MockInvoiceExtractor → deterministic test data
  │
  └─ [LIVE] Azure Document Intelligence
             prebuilt-invoice model
               │
               ▼
             _map_azure_result()
             _apply_confidence_flags()
             _validate_financial_fields()  ← IBAN, VAT, amount checks
             _set_retention()             ← GDPR Art. 5(1)(e)
  │
  ▼
InvoiceExtractionResult (stored in DB + returned via API)
  │
  ├─ overall_confidence >= 0.80 → ReviewStatus.AUTO_APPROVED
  └─ overall_confidence < 0.80 or low_confidence_fields → MANUAL_REVIEW
```

## Data Flow — CV

```
PDF Upload
  │
  ▼
BlobStorageService.upload_document()
  │
  ▼
CVExtractor.extract(blob_url, job_description?)
  │
  ├─ [MOCK] MockCVExtractor
  └─ [LIVE] Azure Document Intelligence (prebuilt-document)
  │
  ▼
Post-processing:
  _classify_role()               → TargetRoleCategory
  _calculate_experience()        → years_of_experience
  _classify_dach_eligibility()   → DACHWorkEligibility (informational)
  _apply_confidence_flags()
  _compute_ats_score(jd)         → ATSJobMatchScore (0-100)
  _generate_recruiter_summary()  → 3-4 sentence ATS note
  _generate_improvement_suggestions()
  _set_retention()
  │
  ▼
CVExtractionResult
```

---

## Azure AI-102 Skill Coverage

| AI-102 Domain | Platform Feature |
|---|---|
| Document Intelligence — prebuilt models | `prebuilt-invoice`, `prebuilt-document` |
| Custom model training guidance | Documented in `docs/deployment.md` |
| Confidence score handling | Per-field confidence, thresholds, flagging |
| Multi-language support | Auto-detection: DE, EN, FR, IT |
| Responsible AI / GDPR | Full Art. 5/6/7/12/15-21 compliance layer |
| Azure Blob Storage integration | Structured upload, SAS URLs, deletion |
| Azure Key Vault | Secrets management, PII encryption keys |
| Application Insights | Structured logging, telemetry |
| Managed Identity | App Service → Key Vault / Blob / SQL |
| Infrastructure as Code | Bicep templates for all resources |
