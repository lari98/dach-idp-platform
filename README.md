# DACH Intelligent Document Processing Platform

> **Production-ready Azure AI portfolio project** — End-to-end PDF processing for
> invoices and CVs/resumes, purpose-built for Germany (DE), Switzerland (CH),
> and Austria (AT). Aligned with the **Azure AI Engineer (AI-102)** certification.

[![CI](https://github.com/your-username/dach-idp-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/dach-idp-platform/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg)](https://fastapi.tiangolo.com)
[![Azure AI](https://img.shields.io/badge/Azure%20AI-Document%20Intelligence-0078D4.svg)](https://azure.microsoft.com/products/ai-services/ai-document-intelligence)
[![GDPR](https://img.shields.io/badge/GDPR-DSGVO%20Compliant-green.svg)](#gdpr--dsgvo-compliance)
[![Mock Mode](https://img.shields.io/badge/demo-mock%20mode-orange.svg)](#quick-start--mock-mode)

---

## What This Project Demonstrates

This is a **senior-level portfolio project** targeting roles at consulting, banking,
finance, HR automation, and enterprise software companies across the DACH region.

**Technical depth covers:**
- Azure AI Document Intelligence (prebuilt + custom model guidance)
- Per-field confidence scoring with automatic manual-review flagging
- DACH-specific validation (IBAN mod-97, VAT rates DE/AT/CH, Swiss QR-Bill)
- Full GDPR/DSGVO compliance workflow (Art. 5/6/7/15-21)
- ATS-style CV scoring and recruiter intelligence
- Multi-language document processing (DE/EN/FR/IT)
- Infrastructure as Code (Azure Bicep)
- Production-grade FastAPI with async SQLAlchemy, structlog, CI/CD

---

## Feature Matrix

### Invoice Processing

| Feature | Detail |
|---|---|
| Vendor name, address, tax ID | With confidence scores |
| Invoice number, date, due date | Parsed to structured date objects |
| Currency | EUR (DE/AT) and CHF (CH) auto-detected |
| Subtotal net, VAT amount, total gross | Cross-validated for consistency |
| VAT rate | Validated against DACH rates (DE: 19%/7%, AT: 20%/10%, CH: 8.1%/2.6%) |
| IBAN | Validated via ISO 7064 mod-97 checksum |
| BIC / Payment reference | Extracted; Swiss QR-Bill reference supported |
| Line items | Description, qty, unit price, VAT per line |
| Low-confidence flag | Per-field threshold; auto-routes to manual review queue |
| Country / language detection | DACH region classification |
| Retention date | HGB §257 / AO §147 / OR Art. 958f compliance |

### CV / Resume Processing

| Feature | Detail |
|---|---|
| Personal info (PII) | Name, email, phone, location, DOB, nationality |
| Work experience | Company, title, dates, duration, description |
| Education | Degree, institution, level (Abitur → PhD), grade |
| Certifications | Name, issuer, date, expiry |
| Skills | Technical / soft / domain (separately categorised) |
| Languages | All languages + proficiency level (A1–C2/Native) |
| German proficiency | Highlighted separately — critical for DACH market |
| ATS score | 0–100, breakdown by skills/experience/education/certifications |
| Keyword matching | Matched vs. missing keywords vs. provided JD |
| Target role category | Inferred from skills taxonomy |
| Years of experience | Calculated from work history |
| DACH work eligibility | EU/EEA/Swiss/Permit Required (informational, not legal) |
| Recruiter summary | AI-generated 3-4 sentence ATS note |
| Improvement suggestions | Actionable DACH-market CV improvement tips |

### GDPR / DSGVO Compliance

| Feature | Regulation |
|---|---|
| Explicit consent recording | Art. 6(1)(a), Art. 7 |
| Consent withdrawal | Art. 7(3) |
| Purpose limitation | Art. 5(1)(b) |
| Data minimisation | Art. 5(1)(c) |
| Right of access (export) | Art. 15 |
| Right to rectification | Art. 16 |
| Right to erasure ("Right to be Forgotten") | Art. 17 |
| Right to restriction | Art. 18 |
| Right to data portability | Art. 20 |
| Immutable audit trail | Art. 5(2) — Accountability |
| PII pseudonymisation / masking | Art. 25 — Privacy by design |
| Retention management | Art. 5(1)(e) + HGB §257/AO §147/OR 958f |
| DSR 30-day deadline tracking | Art. 12(3) |
| CH revDSG compliance notes | In force 01.09.2023 |

---

## Architecture

```
PDF Upload (Invoice / CV)
       │
       ▼
  Azure App Service (FastAPI)
       │
  ┌────┴────────────────┐
  │                     │
  ▼                     ▼
Azure Blob           Azure AI Document Intelligence
Storage              (prebuilt-invoice / prebuilt-document)
(encrypted,          Language: DE, EN, FR, IT
 private)            Confidence: per field
       │
       ▼
  Extraction Engine
  ├── IBAN/VAT/amount validation
  ├── Confidence flagging + review routing
  ├── ATS scoring (CVs)
  ├── DACH eligibility classification
  ├── GDPR post-processing
  └── Audit logging
       │
       ▼
  Azure SQL Database
  ├── documents_invoice
  ├── documents_cv
  ├── consent_records
  ├── audit_logs
  └── data_subject_requests
       │
       ▼
  Power BI Service
  ├── Invoice Analytics
  ├── CV Pipeline
  └── GDPR Compliance
```

See [`docs/architecture.md`](docs/architecture.md) for full component diagrams.

---

## Quick Start — Mock Mode

No Azure account or credentials required. Runs entirely locally.

```bash
# 1. Clone and set up
git clone https://github.com/your-username/dach-idp-platform.git
cd dach-idp-platform
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Configure (mock mode is the default)
cp .env.example .env
# APP_MODE=mock is already set — no Azure credentials needed

# 3. Run the interactive demo
python scripts/demo.py

# 4. Start the API server
uvicorn app.main:app --reload --port 8000

# 5. Open API docs
# → http://localhost:8000/docs   (Swagger UI)
# → http://localhost:8000/redoc  (ReDoc)
```

### Run with Docker (mock mode)

```bash
docker-compose up
# API available at http://localhost:8000
```

---

## Quick Start — Live Mode (Azure)

```bash
# 1. Create Azure resources
az group create --name rg-dach-idp-dev --location germanywestcentral
az deployment group create \
  --resource-group rg-dach-idp-dev \
  --template-file infrastructure/main.bicep \
  --parameters environment=dev sqlAdminUsername=sqladmin sqlAdminPassword=<secure-password>

# 2. Configure .env
cp .env.example .env
# Fill in:
#   APP_MODE=live
#   AZURE_DOC_INTEL_ENDPOINT=https://di-dach-idp-dev.cognitiveservices.azure.com/
#   AZURE_DOC_INTEL_KEY=<key from Azure Portal>
#   AZURE_STORAGE_CONNECTION_STRING=<connection string>
#   AZURE_SQL_SERVER=sql-dach-idp-dev.database.windows.net
#   ...

# 3. Start
uvicorn app.main:app --reload
```

---

## API Reference

### Invoices

```
POST   /api/v1/invoices/upload           Upload & extract invoice PDF
GET    /api/v1/invoices/                 List invoices (filter: country, review status)
GET    /api/v1/invoices/{id}             Full extraction result with confidence scores
PATCH  /api/v1/invoices/{id}/review      Submit manual review decision
DELETE /api/v1/invoices/{id}             GDPR Art. 17 erasure
GET    /api/v1/invoices/{id}/audit       Full audit trail
```

### CVs / Resumes

```
POST   /api/v1/cvs/upload                Upload & extract CV (+ optional JD for ATS scoring)
GET    /api/v1/cvs/                      List CVs (filter: role, ATS score, PII masked)
GET    /api/v1/cvs/{id}                  Full extraction result
POST   /api/v1/cvs/{id}/score            Re-score against a new job description
GET    /api/v1/cvs/{id}/recruiter        Recruiter summary + improvement suggestions
PATCH  /api/v1/cvs/{id}/mask-pii         Apply PII pseudonymisation
DELETE /api/v1/cvs/{id}                  GDPR Art. 17 erasure
GET    /api/v1/cvs/{id}/audit            Audit trail
```

### GDPR / DSGVO

```
POST   /api/v1/gdpr/consent              Grant explicit consent
POST   /api/v1/gdpr/consent/withdraw     Withdraw consent
GET    /api/v1/gdpr/consent/{id}         Get consent record

POST   /api/v1/gdpr/dsr                  Submit Data Subject Request
GET    /api/v1/gdpr/dsr                  List all DSRs
GET    /api/v1/gdpr/dsr/{id}             DSR status + deadline
POST   /api/v1/gdpr/dsr/{id}/erasure     Execute Art. 17 erasure
POST   /api/v1/gdpr/dsr/{id}/access      Execute Art. 15 export

GET    /api/v1/gdpr/audit                Query audit log
GET    /api/v1/gdpr/health               GDPR compliance health check
```

### Upload Example (curl)

```bash
# Upload invoice
curl -X POST http://localhost:8000/api/v1/invoices/upload \
  -F "file=@tests/fixtures/sample_invoice_de.pdf" \
  -F "consent_id=cns-optional"

# Upload CV with JD for ATS scoring
curl -X POST http://localhost:8000/api/v1/cvs/upload \
  -F "file=@tests/fixtures/sample_cv.pdf" \
  -F "job_description=Senior Azure Data Scientist. Required: Python, Azure ML, TensorFlow..."

# Submit erasure request
curl -X POST http://localhost:8000/api/v1/gdpr/dsr \
  -H "Content-Type: application/json" \
  -d '{"request_type": "erasure", "data_subject_identifier": "candidate@example.com"}'
```

---

## Running Tests

```bash
# All tests (mock mode, no Azure needed)
pytest tests/ -v --asyncio-mode=auto

# With coverage
pytest tests/ --cov=app --cov-report=term-missing

# Specific test classes
pytest tests/test_invoice_extractor.py::TestIBANValidator -v
pytest tests/test_cv_extractor.py::TestDACHEligibility -v
pytest tests/test_cv_extractor.py::TestPIIMasker -v
```

---

## Project Structure

```
dach-idp-platform/
├── app/
│   ├── main.py                  # FastAPI app, middleware, lifespan
│   ├── config.py                # Pydantic Settings, live/mock switching
│   ├── models/
│   │   ├── invoice.py           # Invoice Pydantic models (25+ fields)
│   │   ├── cv.py                # CV Pydantic models (30+ fields, ATS)
│   │   └── gdpr.py              # Consent, DSR, audit, PII masking models
│   ├── services/
│   │   ├── invoice_extractor.py # Azure Doc Intel + DACH validation
│   │   ├── cv_extractor.py      # CV extraction + ATS scoring
│   │   ├── blob_storage.py      # Azure Blob / local filesystem
│   │   ├── gdpr_service.py      # Consent, DSR, erasure, export
│   │   ├── audit_service.py     # Immutable audit logging
│   │   └── pii_masker.py        # PII pseudonymisation
│   ├── api/
│   │   ├── invoices.py          # Invoice endpoints
│   │   ├── cvs.py               # CV endpoints
│   │   └── gdpr.py              # GDPR endpoints
│   ├── database/
│   │   ├── models.py            # SQLAlchemy ORM (Azure SQL + SQLite)
│   │   └── connection.py        # Async engine, session factory
│   ├── mock/
│   │   ├── mock_invoice.py      # 4 realistic DACH invoice scenarios
│   │   └── mock_cv.py           # 4 realistic DACH CV personas
│   └── utils/
│       └── validators.py        # IBAN (mod-97), VAT, QR-Bill validators
├── tests/
│   ├── conftest.py              # Forces mock mode, shared fixtures
│   ├── test_invoice_extractor.py # 20+ tests
│   └── test_cv_extractor.py     # 25+ tests
├── infrastructure/
│   └── main.bicep               # Full Azure IaC: Doc Intel, Blob, SQL, App Service
├── docs/
│   ├── architecture.md          # Architecture diagram + data flow
│   └── gdpr-compliance.md       # Full GDPR article mapping
├── powerbi/
│   └── README.md                # DAX formulas + dashboard design guide
├── scripts/
│   └── demo.py                  # Interactive end-to-end demo
├── .github/workflows/ci.yml     # Lint + test + Docker build CI
├── Dockerfile                   # Multi-stage Python 3.11
├── docker-compose.yml           # Local dev with mock mode
├── requirements.txt             # All dependencies pinned
└── .env.example                 # All configuration options documented
```

---

## Azure AI-102 Alignment

This project directly demonstrates the following AI-102 exam domains:

**Plan and manage Azure AI solutions**
- Azure Cognitive Services provisioning (Bicep)
- Managed Identity authentication pattern
- Key Vault secrets management

**Implement content moderation and document processing**
- Azure AI Document Intelligence prebuilt-invoice model
- Custom model training workflow (documented)
- Confidence score handling and manual review routing

**Implement natural language processing**
- Multi-language detection (DE/EN/FR/IT)
- Named entity recognition patterns (CV extraction)
- Text classification (role category inference)

**Implement knowledge mining and document intelligence**
- Structured data extraction from unstructured PDFs
- Field confidence scoring
- Layout analysis for CVs

**Implement and manage AI models responsibly**
- GDPR/DSGVO compliance as a first-class concern
- PII identification and pseudonymisation
- Audit trail for all AI-driven decisions
- Human-in-the-loop (manual review queue)
- Disclaimer on automated DACH eligibility classification

---

## GDPR / DSGVO Compliance

Applicable regulations:
- **DSGVO** (Datenschutz-Grundverordnung) — Germany
- **DSG 2018** (Datenschutzgesetz) — Austria
- **revDSG / nDSG** — Switzerland (in force 01.09.2023)

Key implementations:
- **Consent**: `POST /api/v1/gdpr/consent` — records purpose, legal basis, version, IP hash
- **Withdrawal**: `POST /api/v1/gdpr/consent/withdraw` — immediately processable
- **Access (Art. 15)**: Machine-readable JSON export with checksum
- **Erasure (Art. 17)**: Blob deletion + DB anonymisation in single transaction
- **Retention**: Invoices — 2555 days (HGB §257); CVs — 365 days; Audit — 10 years
- **PII masking**: `PATCH /api/v1/cvs/{id}/mask-pii` — pseudonymisation of 6 fields
- **Audit log**: Every operation logged with actor, timestamp, outcome

> **Note on work eligibility classification**: The DACH work eligibility field is
> informational only, based on stated nationality in the CV. It is NOT a legal
> determination and must never be the sole basis for a hiring or rejection decision.
> Always consult qualified immigration counsel. This is consistent with GDPR Art. 22
> requirements around automated decision-making.

---

## Technology Stack

| Layer | Technology |
|---|---|
| API Framework | FastAPI 0.111 (async, OpenAPI 3.1) |
| Language | Python 3.11 |
| AI / OCR | Azure AI Document Intelligence (Form Recognizer v3) |
| Storage | Azure Blob Storage (AES-256, SSE) |
| Database | Azure SQL / SQLite (SQLAlchemy async) |
| Auth | Azure Managed Identity / Azure AD |
| Secrets | Azure Key Vault |
| Logging | structlog (structured JSON) + App Insights |
| Validation | Pydantic v2, custom IBAN/VAT validators |
| IaC | Azure Bicep |
| Containerisation | Docker (multi-stage), Docker Compose |
| CI/CD | GitHub Actions |
| Testing | pytest + pytest-asyncio (mock mode, no Azure needed) |
| Visualisation | Power BI Service (DAX formulas provided) |

---

## Languages & Regions

| Language | Locale | Region |
|---|---|---|
| German | `de` | DE, AT, CH |
| English | `en` | International |
| French | `fr` | CH (Romandy), FR |
| Italian | `it` | CH (Ticino), IT |

| Currency | Countries |
|---|---|
| EUR | Germany (DE), Austria (AT) |
| CHF | Switzerland (CH) |

---

## Deployment Options

| Option | Command |
|---|---|
| Local (mock mode) | `uvicorn app.main:app --reload` |
| Docker (mock mode) | `docker-compose up` |
| Azure App Service | Deploy via GitHub Actions or `az webapp deploy` |
| Azure Container Apps | Add `containerapp.yml` (Bicep extension available) |

---

## Contributing & License

This is a portfolio/demonstration project. Contributions welcome via pull request.

**License**: MIT

---

## Contact

Built by **Muhammad Umer** · [umerlari1998@gmail.com](mailto:umerlari1998@gmail.com)

Targeting Azure AI Engineer, Data & AI Consultant, and AI Platform Engineer roles
in the DACH region (DE/AT/CH) and internationally.

---

*This project uses general enterprise-grade best practices. It does not replicate
any proprietary ATS system, internal tool, or client system. All mock data is
entirely fictional.*
