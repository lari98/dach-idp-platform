# Power BI Integration Guide — DACH IDP Platform

## Overview

Three Power BI dashboards are provided for this platform:

1. **Invoice Analytics Dashboard** — Volume, amounts, VAT, vendor analysis, manual review queue
2. **CV Pipeline Dashboard** — ATS scores, role categories, eligibility, skills heatmap
3. **GDPR Compliance Dashboard** — Consent status, DSR tracking, retention schedule, audit log

---

## Data Sources

Connect Power BI to **Azure SQL Database** using DirectQuery or Import mode.

### Connection

```
Server:   <your-server>.database.windows.net
Database: dach-idp
Auth:     SQL / Azure AD (recommended)
```

### Key Tables

| Table | Description |
|---|---|
| `documents_invoice` | Invoice extraction results |
| `documents_cv` | CV extraction results |
| `consent_records` | GDPR consent records |
| `audit_logs` | Immutable audit trail |
| `data_subject_requests` | DSR tracking |

---

## Invoice Analytics Dashboard

### KPI Cards
- Total Invoices Processed (month)
- Auto-Approved vs. Manual Review Rate
- Average Extraction Confidence
- Total Invoice Volume (EUR + CHF)
- Average Processing Time

### Charts

**Invoice Volume by Country (Bar Chart)**
```DAX
Invoice Count DE = CALCULATE(COUNTROWS(documents_invoice), documents_invoice[country_detected] = "DE")
Invoice Count AT = CALCULATE(COUNTROWS(documents_invoice), documents_invoice[country_detected] = "AT")
Invoice Count CH = CALCULATE(COUNTROWS(documents_invoice), documents_invoice[country_detected] = "CH")
```

**Confidence Score Distribution (Histogram)**
```DAX
Confidence Bucket =
SWITCH(TRUE(),
  documents_invoice[overall_confidence] >= 0.90, "High (≥90%)",
  documents_invoice[overall_confidence] >= 0.75, "Medium (75-90%)",
  documents_invoice[overall_confidence] >= 0.60, "Low (60-75%)",
  "Critical (<60%)"
)
```

**Monthly Invoice Volume Trend (Line Chart)**
```DAX
Monthly Volume = 
CALCULATE(
  SUM(documents_invoice[total_gross]),
  DATESMTD(documents_invoice[uploaded_at])
)
```

**VAT Rate Distribution by Country (Stacked Bar)**
```DAX
VAT 19% Count = CALCULATE(COUNTROWS(documents_invoice), documents_invoice[vat_rate] = 19.0)
VAT 20% Count = CALCULATE(COUNTROWS(documents_invoice), documents_invoice[vat_rate] = 20.0)
VAT 8.1% Count = CALCULATE(COUNTROWS(documents_invoice), documents_invoice[vat_rate] = 8.1)
```

**Manual Review Queue (Table Visual)**
Columns: Document ID | Vendor | Total | Country | Confidence | Days Pending

---

## CV Pipeline Dashboard

### KPI Cards
- CVs Processed (period)
- Average ATS Score
- Candidates Requiring Review
- Work Permit Required (count)
- Average Years of Experience

### Charts

**ATS Score Distribution (Box Plot / Bar)**
```DAX
ATS Score Bucket =
SWITCH(TRUE(),
  documents_cv[ats_score] >= 80, "Strong Match (80-100)",
  documents_cv[ats_score] >= 60, "Good Match (60-79)",
  documents_cv[ats_score] >= 40, "Partial Match (40-59)",
  "Weak Match (<40)"
)
```

**Role Category Breakdown (Donut Chart)**
```DAX
Roles = GROUPBY(documents_cv, documents_cv[target_role_category], "Count", COUNTX(CURRENTGROUP(), documents_cv[id]))
```

**DACH Work Eligibility (Stacked Bar by Country)**
```DAX
EU Citizens = CALCULATE(COUNTROWS(documents_cv), documents_cv[dach_eligibility] = "eu_eea_citizen")
Swiss Citizens = CALCULATE(COUNTROWS(documents_cv), documents_cv[dach_eligibility] = "swiss_citizen")
Permit Required = CALCULATE(COUNTROWS(documents_cv), documents_cv[dach_eligibility] = "work_permit_required")
```

**German Language Proficiency (Gauge / Bar)**
```DAX
Native German = CALCULATE(COUNTROWS(documents_cv), documents_cv[german_proficiency] = "native")
C1 German = CALCULATE(COUNTROWS(documents_cv), documents_cv[german_proficiency] = "C1")
B2 German = CALCULATE(COUNTROWS(documents_cv), documents_cv[german_proficiency] = "B2")
```

**Experience vs ATS Score (Scatter Plot)**
X-axis: `years_of_experience`
Y-axis: `ats_score`
Size: `overall_confidence`

---

## GDPR Compliance Dashboard

### KPI Cards
- Active Consents
- Pending DSRs
- Overdue DSRs (⚠️ highlight red if > 0)
- Documents Expiring in 30 Days
- Audit Log Entries (30 days)

### Charts

**DSR Status Breakdown (Donut)**
```DAX
DSR Received = CALCULATE(COUNTROWS(data_subject_requests), data_subject_requests[status] = "received")
DSR In Progress = CALCULATE(COUNTROWS(data_subject_requests), data_subject_requests[status] = "in_progress")
DSR Completed = CALCULATE(COUNTROWS(data_subject_requests), data_subject_requests[status] = "completed")
DSR Overdue = CALCULATE(COUNTROWS(data_subject_requests), data_subject_requests[status] = "overdue")
```

**DSR Response Time (Bar Chart)**
```DAX
Avg Response Days = 
AVERAGEX(
  FILTER(data_subject_requests, data_subject_requests[completed_at] <> BLANK()),
  DATEDIFF(data_subject_requests[received_at], data_subject_requests[completed_at], DAY)
)
```

**Retention Schedule (Table — documents expiring within 90 days)**
```DAX
Expiring Soon = 
FILTER(
  documents_invoice,
  DATEDIFF(TODAY(), DATEVALUE(documents_invoice[retention_until]), DAY) <= 90
)
```

**Audit Actions Over Time (Area Chart)**
```DAX
Uploads Per Day = CALCULATE(COUNTROWS(audit_logs), audit_logs[action] = "upload")
Deletions Per Day = CALCULATE(COUNTROWS(audit_logs), audit_logs[action] = "delete")
DSR Events Per Day = CALCULATE(COUNTROWS(audit_logs), audit_logs[action] IN {"dsr_received", "dsr_completed"})
```

---

## Row-Level Security (RLS)

For enterprise deployments, implement RLS so recruiters only see CVs in their team:

```DAX
[actor_id] = USERPRINCIPALNAME()
```

---

## Refreshing Data

- **Import Mode**: Schedule refresh every 4 hours via Power BI Service
- **DirectQuery**: Live — data always current, but higher DB load
- **Recommended for GDPR audit**: Import with daily refresh + retain 90 days history

---

## Notes

- Power BI datasets should **never** display unmasked PII fields directly
- Use row-level security to enforce recruiter/HR access boundaries
- Audit log data should be read-only in Power BI (no write-back)
- All dashboards should be published to a private workspace, not public
