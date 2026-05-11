"""
app/models/cv.py
================
Pydantic models for CV/resume extraction results.
ATS-style scoring, keyword matching, DACH work eligibility notes.
Supports DE, EN, FR, IT.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, EmailStr, Field


class EducationLevel(str, Enum):
    AUSBILDUNG = "ausbildung"           # Vocational training (DE/AT)
    BACHELOR = "bachelor"
    MASTER = "master"
    PHD = "phd"
    MBA = "mba"
    DIPLOM = "diplom"                   # German Diplom
    FACHHOCHSCHULE = "fachhochschule"  # University of Applied Sciences
    MATURA = "matura"                   # AT/CH secondary
    ABITUR = "abitur"                   # DE secondary
    OTHER = "other"


class LanguageProficiency(str, Enum):
    NATIVE = "native"
    C2 = "C2"
    C1 = "C1"
    B2 = "B2"
    B1 = "B1"
    A2 = "A2"
    A1 = "A1"
    BASIC = "basic"


class TargetRoleCategory(str, Enum):
    ENGINEERING = "engineering"
    DATA_SCIENCE = "data_science"
    FINANCE = "finance"
    CONSULTING = "consulting"
    MANAGEMENT = "management"
    SALES = "sales"
    MARKETING = "marketing"
    HR = "hr"
    LEGAL = "legal"
    OPERATIONS = "operations"
    OTHER = "other"


class DACHWorkEligibility(str, Enum):
    """
    Informational classification only — not a legal determination.
    Always consult qualified immigration counsel for binding advice.
    """
    EU_EEA_CITIZEN = "eu_eea_citizen"
    SWISS_CITIZEN = "swiss_citizen"
    BILATERAL_AGREEMENT = "bilateral_agreement"  # CH-EU agreement
    WORK_PERMIT_REQUIRED = "work_permit_required"
    BLUE_CARD_ELIGIBLE = "eu_blue_card_eligible"
    UNKNOWN = "unknown"


class WorkExperienceEntry(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[str] = None    # ISO date or "MM/YYYY"
    end_date: Optional[str] = None      # ISO date, "MM/YYYY", or "present"
    is_current: bool = False
    duration_months: Optional[int] = None
    description: Optional[str] = None
    location: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class EducationEntry(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    level: Optional[EducationLevel] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    grade: Optional[str] = None    # e.g. "1.5" (DE) or "Distinction"
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class LanguageEntry(BaseModel):
    language: str
    proficiency: Optional[LanguageProficiency] = None
    is_native: bool = False
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class CertificationEntry(BaseModel):
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    expiry: Optional[str] = None
    credential_id: Optional[str] = None
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class ATSJobMatchScore(BaseModel):
    """
    ATS-style job match scoring.
    Provide a job description to get keyword matching.
    """
    score: float = Field(0.0, ge=0.0, le=100.0, description="Match score 0-100")
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    score_breakdown: Dict[str, float] = Field(
        default_factory=dict,
        description="e.g. {'skills': 45, 'experience': 30, 'education': 15, 'certifications': 10}"
    )
    job_description_used: Optional[str] = Field(None, description="Truncated JD snippet used for scoring")


class CVExtractionResult(BaseModel):
    """
    Complete structured result of CV/resume extraction.
    GDPR-aware: PII fields are masked when pii_masked=True.
    Includes ATS scoring, DACH work eligibility notes,
    recruiter summary, and candidate improvement suggestions.
    """

    # ── Document metadata ──────────────────────────────────────────
    document_id: str
    blob_url: Optional[str] = None
    original_filename: str
    uploaded_at: str
    language_detected: Optional[str] = None

    # ── Personal info (PII — masked under GDPR where required) ────
    full_name: Optional[str] = Field(None, description="[PII] Full name")
    email: Optional[str] = Field(None, description="[PII] Email address")
    phone: Optional[str] = Field(None, description="[PII] Phone number")
    location: Optional[str] = Field(None, description="[PII] City/Country")
    linkedin_url: Optional[str] = Field(None, description="[PII] LinkedIn profile")
    website: Optional[str] = None
    date_of_birth: Optional[str] = Field(None, description="[PII] DOB if present")
    nationality: Optional[str] = Field(None, description="[PII] Nationality if stated")

    # ── Professional profile ───────────────────────────────────────
    target_role_category: Optional[TargetRoleCategory] = None
    current_title: Optional[str] = None
    years_of_experience: Optional[float] = Field(
        None, description="Calculated total years of professional experience"
    )
    summary_text: Optional[str] = Field(None, description="Candidate's own summary/objective")

    # ── Structured experience & education ─────────────────────────
    work_experience: List[WorkExperienceEntry] = Field(default_factory=list)
    education: List[EducationEntry] = Field(default_factory=list)
    certifications: List[CertificationEntry] = Field(default_factory=list)

    # ── Skills ───────────────────────────────────────────────────
    technical_skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    domain_skills: List[str] = Field(default_factory=list)
    all_skills: List[str] = Field(default_factory=list)

    # ── Languages ─────────────────────────────────────────────────
    languages: List[LanguageEntry] = Field(default_factory=list)
    german_proficiency: Optional[LanguageProficiency] = Field(
        None, description="German language level — important for DACH market"
    )

    # ── ATS scoring ───────────────────────────────────────────────
    ats_score: Optional[ATSJobMatchScore] = None

    # ── Recruiter intelligence ────────────────────────────────────
    recruiter_summary: Optional[str] = Field(
        None,
        description=(
            "AI-generated 3-4 sentence recruiter summary. "
            "Suitable for internal ATS notes. Not to be shared without consent."
        )
    )
    candidate_improvement_suggestions: List[str] = Field(
        default_factory=list,
        description="Actionable suggestions to improve the CV/application for DACH market"
    )

    # ── DACH work eligibility (informational only) ─────────────────
    dach_work_eligibility_note: Optional[str] = Field(
        None,
        description=(
            "Informational note only, based on stated nationality/location in the CV. "
            "NOT a legal determination. Always consult qualified immigration counsel."
        )
    )
    dach_work_eligibility_classification: DACHWorkEligibility = DACHWorkEligibility.UNKNOWN

    # ── Quality ───────────────────────────────────────────────────
    overall_confidence: float = Field(0.0, ge=0.0, le=1.0)
    low_confidence_fields: List[str] = Field(default_factory=list)
    requires_manual_review: bool = False
    validation_warnings: List[str] = Field(default_factory=list)

    # ── GDPR ─────────────────────────────────────────────────────
    consent_id: Optional[str] = None
    pii_masked: bool = False
    retention_until: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "document_id": "cv-2024-001",
                "original_filename": "lebenslauf_max_muster.pdf",
                "full_name": "Max Mustermann",
                "email": "max@example.de",
                "location": "München, DE",
                "years_of_experience": 7.5,
                "target_role_category": "engineering",
                "german_proficiency": "native",
                "ats_score": {
                    "score": 82.5,
                    "matched_keywords": ["Python", "Azure", "Scrum"],
                    "missing_keywords": ["Terraform", "K8s"]
                },
                "dach_work_eligibility_note": (
                    "Candidate states German nationality. Likely eligible to work "
                    "in DE/AT/CH without additional permit. Verify with HR counsel."
                ),
                "pii_masked": False,
                "overall_confidence": 0.89
            }
        }


class CVUploadResponse(BaseModel):
    document_id: str
    message: str
    mode: str
    status: str = "processing"


class CVListItem(BaseModel):
    document_id: str
    original_filename: str
    uploaded_at: str
    full_name: Optional[str] = None   # masked if GDPR
    current_title: Optional[str] = None
    years_of_experience: Optional[float] = None
    ats_score: Optional[float] = None
    target_role_category: Optional[str] = None
    requires_manual_review: bool
    pii_masked: bool
