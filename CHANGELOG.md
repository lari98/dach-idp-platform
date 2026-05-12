# Changelog

All notable changes to the **DACH Intelligent Document Processing Platform** are documented here.

This project follows [Semantic Versioning](https://semver.org/) and an agile release model:
every feature addition is a new tagged version so you can always roll back to any previous state.

---

## [v2.0.0] — 2024-06-01

### Summary
Major feature release adding a recruiter/analytics dashboard, Power BI–ready mock data,
enhanced CV pipeline with ATS keyword matching, DACH work-eligibility notes, risk flags,
and a full review queue. Database schema extended with 13 new CV fields.

### Added

#### Dashboard & Visualisation
- `dashboard/index.html` — self-contained HTML portfolio dashboard (Chart.js, 6 tabs)
  - **Overview tab**: KPI cards (docs processed, manual review rate, GDPR compliance, avg confidence), monthly trend chart, country/language/currency distribution doughnuts
  - **Invoices tab**: vendor table with review rate, status doughnut, VAT-rate distribution bar chart, filters by country/currency/review status
  - **CVs / Candidates tab**: full candidate register, ATS distribution histogram, German proficiency bar, eligibility doughnut, role-category doughnut, top-missing-skills list
  - **Review Queue tab**: invoice queue table + CV review queue with priority badges
  - **GDPR / Compliance tab**: DSR tracking table with deadlines, audit-action frequency chart, DSR-status doughnut, consent-record summary
  - **Anomalies tab**: anomaly-type doughnut, error-rate-by-country bar chart, anomaly log table

#### Power BI Mock Data (`powerbi/mock_data/`)
- `invoices.csv` — 60 DACH invoices (DE/AT/CH, EUR/CHF, realistic IBANs + VAT rates)
- `cvs.csv` — 20 candidate profiles with ATS scores, skills, eligibility, risk flags
- `audit_logs.csv` — 100 immutable audit events
- `dsrs.csv` — 15 Data Subject Requests including overdue examples
- `powerbi/README.md` — DAX formulas, 3 dashboard designs, RLS guidance, refresh schedule

#### Data Generation
- `scripts/generate_mock_data.py` — deterministic Faker-based generator
  - 8 DE + 5 AT + 6 CH vendors with correct IBANs and VAT
  - 20 CV personas spanning 6 role categories and 4 DACH countries
  - Outputs both CSV (Power BI) and JSON (HTML dashboard / API mock)

#### Database Schema — `CVDocument` new fields
| Field | Type | Purpose |
|---|---|---|
| `ats_match_score` | Float | Explicit v2 match score alias (0–100) |
| `matched_keywords_json` | JSON | Keywords found in both CV and JD |
| `missing_keywords_json` | JSON | JD keywords absent from CV |
| `improvement_suggestions_json` | JSON | Actionable DACH-market tips |
| `improvement_suggestion_count` | Integer | Dashboard filter counter |
| `dach_work_eligibility_notes` | Text | Informational eligibility notes (legal disclaimer included) |
| `manual_review_required` | Boolean | Explicit v2 alias for `requires_manual_review` |
| `review_queue_priority` | Integer | 0=low / 1=medium / 2=high |
| `risk_flags_json` | JSON | List of risk-flag strings |
| `missing_work_eligibility` | Boolean | True when eligibility is UNKNOWN |
| `candidate_country` | String(5) | ISO 3166-1 alpha-2 (DE/AT/CH/FR/IT/OTHER) |
| `candidate_language` | String(10) | BCP-47 primary language (de/en/fr/it) |
| `processing_status` | String(30) | pending / processing / complete / failed |

#### CV Extractor Enhancements (`app/services/cv_extractor.py`)
- `_generate_improvement_suggestions()` — DACH-market specific actionable tips
- `_compute_ats_score()` now populates `matched_keywords` and `missing_keywords`
- `manual_review_required` + `review_queue_priority` + `risk_flags` set during post-processing
- `dach_work_eligibility_notes` always includes legal disclaimer text

### Changed
- `app/database/models.py` — `CVDocument` extended (see table above); fully backward-compatible (all new columns nullable or have defaults)
- `app/models/cv.py` — `CVExtractionResult` extended with new Pydantic fields matching DB additions
- `powerbi/README.md` — new DAX measures for v2 metrics, 3-dashboard layout plan updated

### Fixed
- Removed incorrect `ReviewStatus` import from `app/services/cv_extractor.py` (was importing from `app.models.cv` where it doesn't exist; it belongs to `app.models.invoice`)
- Cleaned null bytes (`\x00`) introduced by editor tool in `cv_extractor.py`

### Tests
- All 47 existing tests continue to pass in mock mode (`pytest tests/ -v`)
- No new test files in this release (v2.1.0 roadmap: add dashboard data tests)

---

## [v1.0.0] — 2024-05-01

### Summary
Initial production-ready release of the DACH IDP Platform.

### Added

#### Core Architecture
- FastAPI application with async SQLAlchemy ORM
- Mock mode (`APP_MODE=mock`) — full demo without any Azure credentials
- Azure live mode with App Service + Managed Identity

#### Invoice Processing
- `app/models/invoice.py` — `InvoiceExtractionResult`, `FieldWithConfidence`, `LineItem`, `VendorAddress`
- `app/services/invoice_extractor.py` — Azure Document Intelligence `prebuilt-invoice` integration
- DACH VAT rates: DE 19%/7%, AT 20%/10%, CH 8.1%/2.6%
- ISO 7064 mod-97 IBAN validation (DE:22, AT:20, CH:21 chars)
- Swiss QR-Bill reference validation (mod-10 + ISO 11649)
- `app/mock/mock_invoice.py` — 4 deterministic scenarios (DE/EUR, CH/CHF, AT/EUR, low-confidence)

#### CV / Resume Processing
- `app/models/cv.py` — `CVExtractionResult`, `ATSJobMatchScore`, `DACHWorkEligibility`
- `app/services/cv_extractor.py` — extraction pipeline with role classification, ATS scoring, DACH eligibility
- ATS scoring: 40% skills + 30% experience keywords + 20% education + 10% certifications
- DACH work-eligibility classification with mandatory legal disclaimer
- `app/mock/mock_cv.py` — 4 personas (German engineer, Swiss finance, Senegalese data scientist, Austrian HR)

#### GDPR Compliance
- `app/models/gdpr.py` — `ConsentRecord`, `AuditLogEntry`, `DataSubjectRequest`, `DataExportPackage`
- `app/services/gdpr_service.py` — full GDPR workflow: consent grant/withdraw, DSR submit, erasure, access export
- SHA-256 pseudonymisation, immutable audit logging, 30-day DSR deadline tracking
- Retention regimes: HGB_DE (10yr), AO_DE (10yr), UGB_AT (7yr), OR_CH (10yr), GDPR_CONSENT (3yr)

#### API Endpoints
- `POST/GET /api/v1/invoices/` — upload, list, get, review, delete, audit
- `POST/GET /api/v1/cvs/` — upload with optional JD for ATS, re-score, recruiter summary, PII mask, delete
- `GET/POST /api/v1/gdpr/` — consent, DSR, erasure, access export, compliance health

#### Infrastructure
- `infrastructure/main.bicep` — full Azure IaC (Log Analytics, App Insights, Key Vault, Storage, Document Intelligence, SQL, App Service)
- `Dockerfile` — multi-stage Python 3.11 build
- `docker-compose.yml` — local development with SQLite
- `.github/workflows/ci.yml` — GitHub Actions: lint (ruff) + test + Docker build

#### Tests
- 29 invoice tests + 18 CV tests = **47 tests total**, all passing in mock mode
- `tests/test_invoice_extractor.py` — IBAN, VAT, amounts, mock extraction, DACH rates
- `tests/test_cv_extractor.py` — mock extraction, ATS scoring, DACH eligibility, PII masker

---

## Roadmap

| Version | Target | Theme |
|---|---|---|
| v2.1.0 | TBD | Add v2 unit tests; dashboard data validation tests |
| v2.2.0 | TBD | Webhook notifications for manual-review queue |
| v3.0.0 | TBD | Azure OpenAI GPT-4o integration for freeform extraction |
| v3.1.0 | TBD | Multi-tenant support with Azure AD B2C |
