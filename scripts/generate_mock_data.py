"""
scripts/generate_mock_data.py  [v2.0.0]
==========================================
Generates realistic DACH mock data for:
  - Power BI import (CSV files in powerbi/mock_data/)
  - Dashboard preview (JSON embedded in dashboard/index.html)

Coverage:
  Countries:  DE (40%), AT (25%), CH (25%), OTHER (10%)
  Languages:  de, en, fr, it
  Currencies: EUR, CHF
  Roles:      Engineering, Finance, Data Science, Consulting, HR, Management

Run:  python scripts/generate_mock_data.py
Output:
  powerbi/mock_data/invoices.csv
  powerbi/mock_data/cvs.csv
  powerbi/mock_data/audit_logs.csv
  powerbi/mock_data/consent_records.csv
  powerbi/mock_data/dsrs.csv
  data/mock/dashboard_data.json
"""
from __future__ import annotations

import csv
import json
import os
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

random.seed(42)   # Reproducible data

BASE = Path(__file__).parent.parent
POWERBI_DIR = BASE / "powerbi" / "mock_data"
DATA_DIR = BASE / "data" / "mock"
POWERBI_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ──────────────────────────────────────────────────────────────────────────────
# Reference data
# ──────────────────────────────────────────────────────────────────────────────

DE_VENDORS = [
    ("Müller & Partner GmbH", "DE", "EUR", "DE89370400440532013000", "DE123456789", 19.0),
    ("Bosch Rexroth AG", "DE", "EUR", "DE27200505501265584170", "DE814711817", 19.0),
    ("Siemens Digital Industries", "DE", "EUR", "DE87200400600228481800", "DE812345678", 19.0),
    ("Deutsche Telekom IT GmbH", "DE", "EUR", "DE68210501700012345678", "DE811234567", 19.0),
    ("SAP Beratung GmbH", "DE", "EUR", "DE89500105178221550006", "DE812222222", 19.0),
    ("Bayer Business Services", "DE", "EUR", "DE21200400600228481800", "DE813333333", 19.0),
    ("Kaufland E-Commerce GmbH", "DE", "EUR", "DE91200000001234567890", "DE814444444", 7.0),
    ("Weber & Söhne Steuerberatung", "DE", "EUR", "DE21500105175688870004", "DE815555555", 19.0),
]

AT_VENDORS = [
    ("Wien Tech Consulting KG", "AT", "EUR", "AT611904300234573201", "ATU12345678", 20.0),
    ("Raiffeisen Software GmbH", "AT", "EUR", "AT483200000012345864", "ATU23456789", 20.0),
    ("ÖBB Technologie GmbH", "AT", "EUR", "AT242011128088012345", "ATU34567890", 10.0),
    ("A1 Telekom Österreich AG", "AT", "EUR", "AT141200000010007342", "ATU45678901", 20.0),
    ("Erste Group Services GmbH", "AT", "EUR", "AT611904300234573201", "ATU56789012", 20.0),
]

CH_VENDORS = [
    ("Zürich Data Solutions AG", "CH", "CHF", "CH9300762011623852957", "CHE-123.456.789 MWST", 8.1),
    ("Swiss Re Management AG", "CH", "CHF", "CH5604835012345678009", "CHE-234.567.890 MWST", 8.1),
    ("UBS Business Solutions AG", "CH", "CHF", "CH3608387000001080173", "CHE-345.678.901 MWST", 8.1),
    ("Nestlé Suisse SA", "CH", "CHF", "CH5604835012345678009", "CHE-456.789.012 MWST", 2.6),
    ("ABB Schweiz AG", "CH", "CHF", "CH5481000000012345678", "CHE-567.890.123 MWST", 8.1),
    ("Helvetia Versicherungen AG", "CH", "CHF", "CH2309000000100013534", "CHE-678.901.234 MWST", 8.1),
]

CV_PERSONAS = [
    # (name, email, location, country, nationality, title, role, yoe, skills, german, eligibility, language)
    ("Maximilian Schneider", "m.schneider@example.de", "München, DE", "DE", "German",
     "Senior Software Engineer", "engineering", 8.5,
     ["Python","Azure","Docker","Kubernetes","CI/CD","REST API","Git","SQL","Scrum","Terraform"],
     "native", "eu_eea_citizen", "de"),
    ("Sophie Keller", "sophie.keller@example.ch", "Zürich, CH", "CH", "Swiss",
     "Senior Finance Analyst", "finance", 6.0,
     ["Excel","VBA","Bloomberg","SAP","IFRS","SQL","Power BI","Risk Management","CFA"],
     "native", "swiss_citizen", "de"),
    ("Amara Diallo", "amara.diallo@example.com", "Berlin, DE", "DE", "Senegalese",
     "Data Scientist", "data_science", 4.5,
     ["Python","TensorFlow","PyTorch","Azure ML","Pandas","scikit-learn","SQL","NLP","Spark"],
     "B2", "work_permit_required", "en"),
    ("Laura Gruber", "laura.gruber@example.at", "Wien, AT", "AT", "Austrian",
     "HR Specialist", "hr", 2.5,
     ["SAP HR","MS Office","Recruiting","Onboarding","Arbeitsrecht","Workday"],
     "native", "eu_eea_citizen", "de"),
    ("Thomas Maurer", "t.maurer@example.ch", "Basel, CH", "CH", "Swiss",
     "Management Consultant", "consulting", 10.0,
     ["Strategy","PRINCE2","PowerPoint","Stakeholder Management","Change Management","Excel","SAP"],
     "native", "swiss_citizen", "de"),
    ("Maria Bianchi", "m.bianchi@example.ch", "Lugano, CH", "CH", "Italian",
     "Financial Controller", "finance", 5.0,
     ["SAP FI","IFRS","Excel","Budgeting","Controlling","Oracle Financials","SQL"],
     "B1", "eu_eea_citizen", "it"),
    ("Pierre Dupont", "p.dupont@example.fr", "Genf, CH", "CH", "French",
     "Business Analyst", "consulting", 3.5,
     ["Python","SQL","Tableau","Jira","Scrum","BPMN","Requirements Engineering"],
     "A2", "eu_eea_citizen", "fr"),
    ("Lena Wagner", "lena.wagner@example.de", "Hamburg, DE", "DE", "German",
     "DevOps Engineer", "engineering", 5.0,
     ["Docker","Kubernetes","Terraform","Azure","Jenkins","GitHub Actions","Linux","Python"],
     "native", "eu_eea_citizen", "de"),
    ("Mehmet Yilmaz", "m.yilmaz@example.de", "Stuttgart, DE", "DE", "Turkish",
     "SAP Consultant", "consulting", 7.0,
     ["SAP S/4HANA","SAP FI","SAP CO","ABAP","Business Analysis","German","Excel"],
     "C1", "work_permit_required", "de"),
    ("Anna Hofer", "a.hofer@example.at", "Graz, AT", "AT", "Austrian",
     "Machine Learning Engineer", "data_science", 3.0,
     ["Python","TensorFlow","AWS","MLflow","SQL","Pandas","Feature Engineering"],
     "native", "eu_eea_citizen", "de"),
    ("Lukas Brunner", "l.brunner@example.ch", "Bern, CH", "CH", "Swiss",
     "Risk Manager", "finance", 8.0,
     ["Basel III","Risk Modelling","Python","R","Excel","Bloomberg","SQL","IFRS 9"],
     "native", "swiss_citizen", "de"),
    ("Priya Sharma", "p.sharma@example.com", "Frankfurt, DE", "DE", "Indian",
     "Java Developer", "engineering", 6.0,
     ["Java","Spring Boot","Microservices","AWS","Docker","SQL","REST API","Maven"],
     "A1", "work_permit_required", "en"),
    ("Claudia Meier", "c.meier@example.at", "Linz, AT", "AT", "Austrian",
     "HR Business Partner", "hr", 9.0,
     ["SAP HR","Arbeitsrecht","Coaching","Employer Branding","Workday","Talent Management"],
     "native", "eu_eea_citizen", "de"),
    ("Jan de Vries", "j.devries@example.com", "München, DE", "DE", "Dutch",
     "Product Manager", "management", 5.5,
     ["Agile","Scrum","Roadmap","Jira","Stakeholder Management","SQL","Python"],
     "B1", "eu_eea_citizen", "en"),
    ("Fatima Al-Hassan", "f.alhassan@example.com", "Zürich, CH", "CH", "Egyptian",
     "Data Analyst", "data_science", 2.0,
     ["Python","SQL","Power BI","Excel","Tableau","Statistics"],
     "A2", "work_permit_required", "en"),
    ("Stefan Bauer", "s.bauer@example.de", "Berlin, DE", "DE", "German",
     "Cloud Architect", "engineering", 12.0,
     ["Azure","AWS","GCP","Terraform","Kubernetes","Docker","Python","Security"],
     "native", "eu_eea_citizen", "de"),
    ("Elena Fontana", "e.fontana@example.it", "Mailand, IT", "OTHER", "Italian",
     "Marketing Manager", "management", 7.0,
     ["Google Analytics","SEO","CRM","Salesforce","Content Strategy","Italian","English"],
     "B2", "eu_eea_citizen", "it"),
    ("David Müller", "d.mueller@example.de", "Düsseldorf, DE", "DE", "German",
     "Compliance Officer", "finance", 6.5,
     ["MaRisk","KWG","AML","DSGVO","Regulatory Reporting","Excel","Legal"],
     "native", "eu_eea_citizen", "de"),
    ("Isabelle Blanc", "i.blanc@example.fr", "Strasbourg, FR", "OTHER", "French",
     "UX Designer", "management", 4.0,
     ["Figma","UX Research","Prototyping","CSS","Agile","User Testing"],
     "B2", "eu_eea_citizen", "fr"),
    ("Ravi Patel", "r.patel@example.com", "Wien, AT", "AT", "Indian",
     "BI Developer", "data_science", 5.0,
     ["Power BI","SQL","SSAS","Azure Synapse","DAX","Python","ETL"],
     "A1", "work_permit_required", "en"),
]

PROCESSING_STATUSES = ["complete"] * 16 + ["manual_review"] * 3 + ["pending"] * 1

RISK_FLAG_OPTIONS = [
    [], [], [], [],  # most have no flags
    ["low_confidence"],
    ["missing_work_eligibility"],
    ["low_confidence", "missing_work_eligibility"],
    ["duplicate_suspected"],
]


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def rand_date(start_days_ago: int = 365, end_days_ago: int = 1) -> date:
    offset = random.randint(end_days_ago, start_days_ago)
    return date.today() - timedelta(days=offset)


def rand_confidence(low: float = 0.72, high: float = 0.99) -> float:
    return round(random.uniform(low, high), 2)


def rand_amount(low: float, high: float) -> float:
    return round(random.uniform(low, high) / 10) * 10


# ──────────────────────────────────────────────────────────────────────────────
# Invoice generation (60 records)
# ──────────────────────────────────────────────────────────────────────────────

def generate_invoices(n: int = 60) -> List[Dict[str, Any]]:
    rows = []
    all_vendors = (DE_VENDORS * 3) + (AT_VENDORS * 2) + (CH_VENDORS * 2)

    for i in range(n):
        vendor = random.choice(all_vendors)
        vname, country, currency, iban, tax_id, vat_rate = vendor
        net = rand_amount(500, 15000)
        vat = round(net * vat_rate / 100, 2)
        total = round(net + vat, 2)
        confidence = rand_confidence(0.55, 0.99)
        inv_date = rand_date(365, 1)
        lang = "de" if country in ("DE", "AT") else random.choice(["de", "fr", "it"])

        rows.append({
            "document_id": f"inv-{uuid.uuid4().hex[:10]}",
            "original_filename": f"rechnung_{i+1:03d}.pdf",
            "uploaded_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))).isoformat(),
            "vendor_name": vname,
            "country_detected": country,
            "language_detected": lang,
            "currency": currency,
            "invoice_number": f"RE-2024-{i+1:05d}",
            "invoice_date": str(inv_date),
            "due_date": str(inv_date + timedelta(days=30)),
            "vendor_iban": iban,
            "vendor_tax_id": tax_id,
            "subtotal_net": net,
            "vat_rate": vat_rate,
            "vat_amount": vat,
            "total_gross": total,
            "overall_confidence": confidence,
            "requires_manual_review": confidence < 0.75,
            "review_status": "manual_review" if confidence < 0.75 else "auto_approved",
            "processing_status": "manual_review" if confidence < 0.75 else "complete",
            "low_confidence_fields": json.dumps(
                ["vendor_name", "total_gross"] if confidence < 0.65 else
                ["invoice_date"] if confidence < 0.75 else []
            ),
            "pii_masked": False,
            "retention_until": str(inv_date + timedelta(days=2555)),
        })
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# CV generation (20 personas × variation)
# ──────────────────────────────────────────────────────────────────────────────

JD_KEYWORDS = ["Python", "Azure", "SQL", "Docker", "Scrum", "REST API", "CI/CD",
               "Machine Learning", "Power BI", "SAP", "Excel", "Kubernetes",
               "Terraform", "Bloomberg", "IFRS", "Risk Management"]

def generate_cvs() -> List[Dict[str, Any]]:
    rows = []
    for i, persona in enumerate(CV_PERSONAS):
        (name, email, location, country, nationality, title, role, yoe,
         skills, german, eligibility, lang) = persona

        confidence = rand_confidence(0.78, 0.97)
        matched_kw = [k for k in JD_KEYWORDS if k in skills]
        missing_kw = [k for k in JD_KEYWORDS if k not in skills][:6]
        ats = min(100, round(len(matched_kw) / len(JD_KEYWORDS) * 100 + random.uniform(-5, 10), 1))
        suggestions = []
        if german in ("A1", "A2", "B1"):
            suggestions.append("Improve German language skills — most DACH employers require B2+")
        if not any("Certif" in s for s in skills):
            suggestions.append("Add relevant certifications (Azure, SAP, CFA, PMP)")
        if yoe < 3:
            suggestions.append("Add more quantified achievements to work experience")
        if eligibility == "work_permit_required":
            suggestions.append("Mention current work permit status or visa sponsorship need")

        risk_flags = []
        if eligibility == "work_permit_required":
            risk_flags.append("work_permit_required")
        if eligibility == "unknown":
            risk_flags.append("missing_work_eligibility")
        if confidence < 0.80:
            risk_flags.append("low_confidence")

        rows.append({
            "document_id": f"cv-{uuid.uuid4().hex[:10]}",
            "original_filename": f"lebenslauf_{name.lower().replace(' ', '_')}.pdf",
            "uploaded_at": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 180))).isoformat(),
            "full_name": name,
            "email": email,
            "location": location,
            "candidate_country": country,
            "candidate_language": lang,
            "nationality": nationality,
            "current_title": title,
            "target_role_category": role,
            "years_of_experience": yoe,
            "all_skills": json.dumps(skills),
            "technical_skills": json.dumps([s for s in skills if s not in ["Teamarbeit", "Kommunikation", "Scrum"]]),
            "german_proficiency": german,
            "language_detected": lang,
            # v2 fields
            "ats_score": ats,
            "ats_match_score": ats,
            "matched_keywords": json.dumps(matched_kw),
            "missing_keywords": json.dumps(missing_kw),
            "dach_work_eligibility": eligibility,
            "dach_work_eligibility_notes": (
                "Informational only — verify with qualified immigration counsel."
            ),
            "missing_work_eligibility": eligibility == "unknown",
            "improvement_suggestions": json.dumps(suggestions),
            "improvement_suggestion_count": len(suggestions),
            "manual_review_required": confidence < 0.82 or eligibility == "unknown",
            "requires_manual_review": confidence < 0.82 or eligibility == "unknown",
            "review_queue_priority": 2 if eligibility == "unknown" else (1 if confidence < 0.80 else 0),
            "risk_flags": json.dumps(risk_flags),
            "overall_confidence": confidence,
            "processing_status": random.choice(PROCESSING_STATUSES),
            "pii_masked": False,
            "retention_until": str(date.today() + timedelta(days=365)),
        })
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Audit log (100 entries)
# ──────────────────────────────────────────────────────────────────────────────

ACTIONS = ["upload", "extract", "view", "export", "mask_pii", "delete",
           "consent_grant", "dsr_received", "manual_review", "review_approved"]

def generate_audit_logs(n: int = 100) -> List[Dict]:
    rows = []
    for i in range(n):
        ts = datetime.now(timezone.utc) - timedelta(days=random.randint(0, 365))
        rows.append({
            "audit_id": f"aud-{uuid.uuid4().hex[:14]}",
            "timestamp": ts.isoformat(),
            "action": random.choice(ACTIONS),
            "document_id": f"inv-{uuid.uuid4().hex[:8]}" if random.random() > 0.4 else f"cv-{uuid.uuid4().hex[:8]}",
            "document_type": random.choice(["invoice", "cv"]),
            "actor_id": random.choice(["user-001", "user-002", "system", "recruiter-01", "admin-01"]),
            "actor_role": random.choice(["user", "system", "recruiter", "admin"]),
            "outcome": "success" if random.random() > 0.05 else "failure",
        })
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# DSRs (15 records)
# ──────────────────────────────────────────────────────────────────────────────

DSR_TYPES = ["access", "erasure", "portability", "rectification", "objection"]
DSR_STATUSES = ["received", "in_progress", "completed", "completed", "completed"]

def generate_dsrs(n: int = 15) -> List[Dict]:
    rows = []
    for i in range(n):
        received = date.today() - timedelta(days=random.randint(1, 120))
        deadline = received + timedelta(days=30)
        status = random.choice(DSR_STATUSES)
        rows.append({
            "dsr_id": f"dsr-{uuid.uuid4().hex[:10]}",
            "request_type": random.choice(DSR_TYPES),
            "received_at": str(received),
            "deadline": str(deadline),
            "status": "overdue" if deadline < date.today() and status != "completed" else status,
            "days_to_deadline": (deadline - date.today()).days,
        })
    return rows


# ──────────────────────────────────────────────────────────────────────────────
# Write CSV files
# ──────────────────────────────────────────────────────────────────────────────

def write_csv(path: Path, rows: List[Dict]) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Written: {path} ({len(rows)} rows)")


def main():
    print("Generating DACH IDP mock data (v2.0.0)...")

    invoices = generate_invoices(60)
    cvs = generate_cvs()
    audit = generate_audit_logs(100)
    dsrs = generate_dsrs(15)

    # Power BI CSVs
    write_csv(POWERBI_DIR / "invoices.csv", invoices)
    write_csv(POWERBI_DIR / "cvs.csv", cvs)
    write_csv(POWERBI_DIR / "audit_logs.csv", audit)
    write_csv(POWERBI_DIR / "dsrs.csv", dsrs)

    # Dashboard JSON
    dashboard_data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "invoices": invoices,
        "cvs": cvs,
        "audit_logs": audit[:50],
        "dsrs": dsrs,
        "summary": {
            "total_invoices": len(invoices),
            "total_cvs": len(cvs),
            "invoices_manual_review": sum(1 for r in invoices if r["requires_manual_review"]),
            "cvs_manual_review": sum(1 for r in cvs if r["manual_review_required"]),
            "cvs_missing_eligibility": sum(1 for r in cvs if r["missing_work_eligibility"]),
            "avg_invoice_confidence": round(sum(r["overall_confidence"] for r in invoices) / len(invoices), 3),
            "avg_cv_confidence": round(sum(r["overall_confidence"] for r in cvs) / len(cvs), 3),
            "avg_ats_score": round(sum(r["ats_score"] for r in cvs) / len(cvs), 1),
            "total_volume_eur": round(sum(r["total_gross"] for r in invoices if r["currency"] == "EUR"), 2),
            "total_volume_chf": round(sum(r["total_gross"] for r in invoices if r["currency"] == "CHF"), 2),
        },
    }

    with open(DATA_DIR / "dashboard_data.json", "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  Written: {DATA_DIR / 'dashboard_data.json'}")
    print(f"\nSummary:")
    for k, v in dashboard_data["summary"].items():
        print(f"  {k}: {v}")
    print("\nDone. Import CSVs into Power BI from powerbi/mock_data/")


if __name__ == "__main__":
    main()
