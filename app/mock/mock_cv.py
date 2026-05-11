"""
app/mock/mock_cv.py
====================
Mock CV extractor — returns realistic DACH CV data.

Includes 4 representative personas:
  1. Senior German Software Engineer (high confidence, EU citizen)
  2. Swiss Finance Analyst (high confidence, Swiss citizen)
  3. International Data Scientist applying in DACH (non-EU, permit required)
  4. Junior Austrian HR candidate (low experience, missing fields)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.models.cv import (
    ATSJobMatchScore,
    CVExtractionResult,
    CertificationEntry,
    DACHWorkEligibility,
    EducationEntry,
    EducationLevel,
    LanguageEntry,
    LanguageProficiency,
    TargetRoleCategory,
    WorkExperienceEntry,
)


MOCK_CVS = [
    # ── CV 1: Senior German Software Engineer ───────────────────────────
    {
        "full_name": "Maximilian Schneider",
        "email": "max.schneider@example.de",
        "phone": "+49 89 123 456 78",
        "location": "München, Deutschland",
        "linkedin_url": "linkedin.com/in/max-schneider-dev",
        "nationality": "German",
        "current_title": "Senior Software Engineer",
        "years_of_experience": 8.5,
        "target_role_category": TargetRoleCategory.ENGINEERING,
        "work_experience": [
            WorkExperienceEntry(company="BMW Group Digital", title="Senior Software Engineer", start_date="2020-01", end_date="present", is_current=True, duration_months=51, description="Azure cloud migration, Python microservices, CI/CD with GitHub Actions.", location="München", confidence=0.95),
            WorkExperienceEntry(company="Siemens AG", title="Software Developer", start_date="2016-06", end_date="2019-12", duration_months=42, description="SAP integration, REST APIs, Java Spring Boot.", location="München", confidence=0.93),
        ],
        "education": [
            EducationEntry(institution="Technische Universität München", degree="M.Sc. Informatik", level=EducationLevel.MASTER, field_of_study="Computer Science", start_date="2014-10", end_date="2016-05", grade="1.7", confidence=0.95),
        ],
        "certifications": [
            CertificationEntry(name="Microsoft Azure AI Engineer Associate (AI-102)", issuer="Microsoft", date="2023-09", confidence=0.96),
            CertificationEntry(name="AZ-204 Azure Developer Associate", issuer="Microsoft", date="2022-05", confidence=0.94),
        ],
        "technical_skills": ["Python", "Azure", "Docker", "Kubernetes", "SQL", "Git", "CI/CD", "Terraform", "REST API", "Java"],
        "soft_skills": ["Teamarbeit", "Kommunikation", "Agile", "Scrum"],
        "all_skills": ["Python", "Azure", "Docker", "Kubernetes", "SQL", "Git", "CI/CD", "Terraform", "REST API", "Java", "Teamarbeit", "Scrum"],
        "languages": [
            LanguageEntry(language="Deutsch", is_native=True, proficiency=LanguageProficiency.NATIVE, confidence=0.99),
            LanguageEntry(language="Englisch", proficiency=LanguageProficiency.C1, confidence=0.95),
        ],
        "german_proficiency": LanguageProficiency.NATIVE,
        "dach_work_eligibility_classification": DACHWorkEligibility.EU_EEA_CITIZEN,
        "dach_work_eligibility_note": "German national. Full work authorisation in DE/AT/CH. No permit required.",
        "overall_confidence": 0.94,
        "requires_manual_review": False,
    },
    # ── CV 2: Swiss Finance Analyst ───────────────────────────────────────
    {
        "full_name": "Sophie Keller",
        "email": "sophie.keller@example.ch",
        "phone": "+41 44 987 65 43",
        "location": "Zürich, Schweiz",
        "nationality": "Swiss",
        "current_title": "Senior Finance Analyst",
        "years_of_experience": 6.0,
        "target_role_category": TargetRoleCategory.FINANCE,
        "work_experience": [
            WorkExperienceEntry(company="UBS AG", title="Senior Finance Analyst", start_date="2021-03", end_date="present", is_current=True, duration_months=38, description="Financial modelling, regulatory reporting (IFRS 9), Bloomberg terminal, risk analysis.", location="Zürich", confidence=0.96),
            WorkExperienceEntry(company="Credit Suisse", title="Junior Analyst", start_date="2018-07", end_date="2021-02", duration_months=31, description="Portfolio analytics, Excel VBA automation, DATEV.", location="Zürich", confidence=0.94),
        ],
        "education": [
            EducationEntry(institution="Universität Zürich", degree="M.Sc. Finance", level=EducationLevel.MASTER, field_of_study="Finance", start_date="2016-09", end_date="2018-06", grade="5.8/6", confidence=0.96),
        ],
        "certifications": [
            CertificationEntry(name="CFA Level II", issuer="CFA Institute", date="2022-08", confidence=0.95),
        ],
        "technical_skills": ["Excel", "VBA", "Bloomberg", "SAP", "IFRS", "SQL", "Power BI"],
        "soft_skills": ["Analytisches Denken", "Präsentation", "Teamleitung"],
        "all_skills": ["Excel", "VBA", "Bloomberg", "SAP", "IFRS", "SQL", "Power BI", "CFA", "Risk Management", "Financial Modelling"],
        "languages": [
            LanguageEntry(language="Deutsch", is_native=True, proficiency=LanguageProficiency.NATIVE, confidence=0.99),
            LanguageEntry(language="Englisch", proficiency=LanguageProficiency.C2, confidence=0.97),
            LanguageEntry(language="Französisch", proficiency=LanguageProficiency.B2, confidence=0.91),
        ],
        "german_proficiency": LanguageProficiency.NATIVE,
        "dach_work_eligibility_classification": DACHWorkEligibility.SWISS_CITIZEN,
        "dach_work_eligibility_note": "Swiss national. Full work authorisation in CH. Benefits from CH-EU bilateral agreement for DE/AT. Inform HR counsel for cross-border arrangements.",
        "overall_confidence": 0.95,
        "requires_manual_review": False,
    },
    # ── CV 3: International Data Scientist (non-EU) ───────────────────────
    {
        "full_name": "Amara Diallo",
        "email": "amara.diallo@example.com",
        "phone": "+49 30 555 1234",
        "location": "Berlin, Deutschland",
        "nationality": "Senegalese",
        "current_title": "Data Scientist",
        "years_of_experience": 4.5,
        "target_role_category": TargetRoleCategory.DATA_SCIENCE,
        "work_experience": [
            WorkExperienceEntry(company="Berlin AI Lab GmbH", title="Data Scientist", start_date="2022-01", end_date="present", is_current=True, duration_months=28, description="NLP models, Python, TensorFlow, Azure ML, A/B testing.", location="Berlin", confidence=0.93),
            WorkExperienceEntry(company="DataCorp Senegal", title="Data Analyst", start_date="2019-07", end_date="2021-12", duration_months=29, description="SQL, Tableau, statistical analysis.", location="Dakar", confidence=0.89),
        ],
        "education": [
            EducationEntry(institution="Humboldt-Universität Berlin", degree="M.Sc. Data Science", level=EducationLevel.MASTER, field_of_study="Data Science", start_date="2019-10", end_date="2021-09", confidence=0.94),
        ],
        "certifications": [
            CertificationEntry(name="Azure Data Scientist Associate (DP-100)", issuer="Microsoft", date="2023-04", confidence=0.95),
        ],
        "technical_skills": ["Python", "TensorFlow", "PyTorch", "SQL", "Azure ML", "Pandas", "scikit-learn", "Spark"],
        "soft_skills": ["Problemlösung", "Kommunikation"],
        "all_skills": ["Python", "TensorFlow", "PyTorch", "SQL", "Azure ML", "Pandas", "scikit-learn", "Spark", "Statistics", "NLP"],
        "languages": [
            LanguageEntry(language="Englisch", is_native=False, proficiency=LanguageProficiency.C2, confidence=0.95),
            LanguageEntry(language="Deutsch", proficiency=LanguageProficiency.B2, confidence=0.90),
            LanguageEntry(language="Französisch", is_native=True, proficiency=LanguageProficiency.NATIVE, confidence=0.99),
        ],
        "german_proficiency": LanguageProficiency.B2,
        "dach_work_eligibility_classification": DACHWorkEligibility.WORK_PERMIT_REQUIRED,
        "dach_work_eligibility_note": (
            "Candidate states Senegalese nationality. A work permit is required for employment in DE/AT/CH. "
            "As a Master's graduate with 4+ years experience in data science, may qualify for EU Blue Card (DE/AT). "
            "Current Blue Card minimum salary threshold DE 2024: €45,552 gross/year (shortage occupations). "
            "NOTE: Informational only. Verify with qualified immigration counsel."
        ),
        "overall_confidence": 0.91,
        "requires_manual_review": False,
    },
    # ── CV 4: Junior Austrian HR (less structured, some fields missing) ──
    {
        "full_name": "Laura Gruber",
        "email": "laura.gruber@example.at",
        "phone": None,
        "location": "Wien, Österreich",
        "nationality": "Austrian",
        "current_title": "HR Assistant",
        "years_of_experience": 1.5,
        "target_role_category": TargetRoleCategory.HR,
        "work_experience": [
            WorkExperienceEntry(company="Raiffeisen Bank International", title="HR Assistant (Praktikum)", start_date="2023-06", end_date="2023-12", duration_months=6, description="Bewerbermanagement, Onboarding-Koordination.", location="Wien", confidence=0.85),
        ],
        "education": [
            EducationEntry(institution="Wirtschaftsuniversität Wien", degree="B.Sc. Wirtschaftswissenschaften", level=EducationLevel.BACHELOR, field_of_study="Business Administration", start_date="2020-10", end_date="2023-05", grade="Gut", confidence=0.90),
        ],
        "certifications": [],
        "technical_skills": ["MS Office", "SAP HR"],
        "soft_skills": ["Kommunikation", "Empathie", "Organisationstalent"],
        "all_skills": ["MS Office", "SAP HR", "Recruiting", "Onboarding", "Kommunikation"],
        "languages": [
            LanguageEntry(language="Deutsch", is_native=True, proficiency=LanguageProficiency.NATIVE, confidence=0.99),
            LanguageEntry(language="Englisch", proficiency=LanguageProficiency.B1, confidence=0.85),
        ],
        "german_proficiency": LanguageProficiency.NATIVE,
        "dach_work_eligibility_classification": DACHWorkEligibility.EU_EEA_CITIZEN,
        "dach_work_eligibility_note": "Austrian national. Full work authorisation in DE/AT/CH.",
        "overall_confidence": 0.82,
        "requires_manual_review": False,
        "validation_warnings": [
            "Phone number not found in document.",
            "No certifications listed — consider adding relevant HR certifications.",
        ],
    },
]


class MockCVExtractor:
    """Returns realistic mock CV data for demo/testing without Azure."""

    async def extract(
        self,
        document_id: str,
        original_filename: str,
        blob_url: str,
        scenario_index: Optional[int] = None,
    ) -> CVExtractionResult:
        if scenario_index is not None:
            data = MOCK_CVS[scenario_index % len(MOCK_CVS)]
        else:
            idx = hash(document_id) % len(MOCK_CVS)
            data = MOCK_CVS[idx]

        now = datetime.now(timezone.utc).isoformat()

        return CVExtractionResult(
            document_id=document_id,
            blob_url=blob_url,
            original_filename=original_filename,
            uploaded_at=now,
            language_detected="de",
            full_name=data.get("full_name"),
            email=data.get("email"),
            phone=data.get("phone"),
            location=data.get("location"),
            linkedin_url=data.get("linkedin_url"),
            nationality=data.get("nationality"),
            current_title=data.get("current_title"),
            years_of_experience=data.get("years_of_experience"),
            target_role_category=data.get("target_role_category"),
            work_experience=data.get("work_experience", []),
            education=data.get("education", []),
            certifications=data.get("certifications", []),
            technical_skills=data.get("technical_skills", []),
            soft_skills=data.get("soft_skills", []),
            all_skills=data.get("all_skills", []),
            languages=data.get("languages", []),
            german_proficiency=data.get("german_proficiency"),
            dach_work_eligibility_classification=data.get("dach_work_eligibility_classification", DACHWorkEligibility.UNKNOWN),
            dach_work_eligibility_note=data.get("dach_work_eligibility_note"),
            overall_confidence=data.get("overall_confidence", 0.0),
            requires_manual_review=data.get("requires_manual_review", False),
            validation_warnings=data.get("validation_warnings", []),
        )
