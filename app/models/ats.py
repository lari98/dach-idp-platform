"""
app/models/ats.py
==================
Pydantic models for the Enterprise ATS (Applicant Tracking System).
Covers Job Requisitions, Candidate Applications, and ATS Scoring.
Multilingual: DE, EN, FR, SV.
Employers: Deloitte, KPMG, Deutsche Bank, Six Group, Accenture, Sparkasse, UBS, etc.
"""
from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class JobLanguage(str, Enum):
    DE = "de"   # German
    EN = "en"   # English
    FR = "fr"   # French
    SV = "sv"   # Swedish


class JobLocation(str, Enum):
    BERLIN = "Berlin, DE"
    FRANKFURT = "Frankfurt, DE"
    MUNICH = "München, DE"
    HAMBURG = "Hamburg, DE"
    ZURICH = "Zürich, CH"
    GENEVA = "Genf, CH"
    VIENNA = "Wien, AT"
    STOCKHOLM = "Stockholm, SE"
    DUSSELDORF = "Düsseldorf, DE"
    REMOTE = "Remote / Hybrid"


class Department(str, Enum):
    CONSULTING = "Consulting"
    AUDIT = "Audit & Assurance"
    TAX = "Tax & Legal"
    FINANCE = "Finance & Accounting"
    RISK = "Risk & Compliance"
    TECHNOLOGY = "Technology & Digital"
    DATA = "Data & Analytics"
    HR = "Human Resources"
    BANKING = "Banking & Capital Markets"
    MANAGEMENT = "Management"


class PipelineStage(str, Enum):
    NEW = "new"
    SCREENED = "screened"
    PHONE_INTERVIEW = "phone_interview"
    TECHNICAL_INTERVIEW = "technical_interview"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    WORKING_STUDENT = "working_student"   # Werkstudent


class SeniorityLevel(str, Enum):
    INTERN = "intern"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    MANAGER = "manager"
    DIRECTOR = "director"
    PARTNER = "partner"


class HardRequirementResult(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# Job Requisition
# ─────────────────────────────────────────────────────────────────────────────

class HardRequirement(BaseModel):
    """A non-negotiable requirement — candidates who fail are auto-rejected."""
    field: str = Field(..., description="e.g. 'min_years_experience', 'required_language', 'work_authorization'")
    value: str = Field(..., description="e.g. '5', 'german_C1', 'EU_EEA'")
    description: Optional[str] = None


class JobRequisition(BaseModel):
    """A job posting — the target document for ATS matching."""
    job_id: str = Field(..., description="Internal job requisition ID, e.g. JR-2024-001")
    title: str = Field(..., description="Job title")
    employer: str = Field(..., description="e.g. Deloitte Deutschland GmbH")
    department: Optional[Department] = None
    location: Optional[str] = None
    remote_possible: bool = False
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    seniority: SeniorityLevel = SeniorityLevel.MID
    language: JobLanguage = JobLanguage.DE

    # Salary
    salary_min: Optional[int] = Field(None, description="Annual gross EUR/CHF/SEK")
    salary_max: Optional[int] = None
    currency: str = "EUR"

    # Job description text (full, as posted)
    description_text: str = Field(..., description="Full JD text in the posting language")

    # Parsed requirements (extracted by ATS engine)
    required_skills: List[str] = Field(default_factory=list,
        description="Canonical skill keys required")
    preferred_skills: List[str] = Field(default_factory=list,
        description="Canonical skill keys preferred (nice to have)")
    required_certifications: List[str] = Field(default_factory=list)
    min_years_experience: Optional[float] = None
    max_years_experience: Optional[float] = None
    required_education: Optional[str] = Field(None,
        description="bachelor / master / phd / vocational")
    required_languages: List[Dict[str, str]] = Field(default_factory=list,
        description="[{'language': 'german_language', 'min_level': 'C1'}]")
    hard_requirements: List[HardRequirement] = Field(default_factory=list)

    # Meta
    posted_date: Optional[date] = None
    closing_date: Optional[date] = None
    is_active: bool = True
    applications_count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# ATS Scoring Result
# ─────────────────────────────────────────────────────────────────────────────

class HardRequirementCheck(BaseModel):
    requirement: str
    result: HardRequirementResult
    detail: str


class ATSScoreBreakdown(BaseModel):
    """Detailed breakdown of how the total ATS score was computed."""
    # Weighted components (weights sum to 100)
    skills_score: float = Field(0.0, description="Technical + required skills match (weight: 35%)")
    experience_score: float = Field(0.0, description="Years of experience vs. requirement (weight: 20%)")
    education_score: float = Field(0.0, description="Education level match (weight: 15%)")
    language_score: float = Field(0.0, description="Language proficiency match (weight: 15%)")
    soft_skills_score: float = Field(0.0, description="Soft skills match (weight: 10%)")
    location_score: float = Field(0.0, description="Location / availability match (weight: 5%)")

    # Raw counts
    required_skills_matched: int = 0
    required_skills_total: int = 0
    preferred_skills_matched: int = 0
    preferred_skills_total: int = 0
    certifications_matched: int = 0
    certifications_required: int = 0


class ATSMatchResult(BaseModel):
    """Full ATS match result for one CV against one Job Requisition."""
    match_id: str
    cv_id: str
    job_id: str
    employer: str
    job_title: str
    matched_at: str   # ISO 8601

    # Overall
    total_score: float = Field(0.0, ge=0.0, le=100.0,
        description="Weighted total ATS score 0-100")
    recommendation: str = Field("",
        description="STRONG_MATCH / GOOD_MATCH / POSSIBLE_MATCH / WEAK_MATCH / NO_MATCH")
    shortlist: bool = False

    # Hard requirements
    hard_requirements_passed: bool = True
    hard_requirement_checks: List[HardRequirementCheck] = Field(default_factory=list)
    auto_rejected: bool = False
    auto_rejection_reason: Optional[str] = None

    # Breakdown
    breakdown: ATSScoreBreakdown = Field(default_factory=ATSScoreBreakdown)

    # Keywords
    matched_skills: List[str] = Field(default_factory=list)
    missing_required_skills: List[str] = Field(default_factory=list)
    missing_preferred_skills: List[str] = Field(default_factory=list)
    bonus_skills: List[str] = Field(default_factory=list,
        description="Skills candidate has that aren't in JD but are relevant")

    # Language
    language_matches: List[Dict[str, str]] = Field(default_factory=list)
    language_gaps: List[Dict[str, str]] = Field(default_factory=list)

    # Improvement
    improvement_tips: List[str] = Field(default_factory=list)
    recruiter_summary: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Candidate Application (pipeline tracking)
# ─────────────────────────────────────────────────────────────────────────────

class CandidateApplication(BaseModel):
    """Tracks a candidate's journey through the recruitment pipeline."""
    application_id: str
    cv_id: str
    job_id: str
    candidate_name: Optional[str] = None   # PII — masked in GDPR mode
    applied_at: str
    current_stage: PipelineStage = PipelineStage.NEW
    stage_history: List[Dict[str, str]] = Field(default_factory=list,
        description="[{'stage': 'screened', 'timestamp': '...', 'note': '...'}]")
    ats_score: Optional[float] = None
    shortlisted: bool = False
    recruiter_notes: Optional[str] = None
    days_in_pipeline: int = 0
    next_action: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# API request/response schemas
# ─────────────────────────────────────────────────────────────────────────────

class JobRequisitionCreate(BaseModel):
    title: str
    employer: str
    department: Optional[Department] = None
    location: Optional[str] = None
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    seniority: SeniorityLevel = SeniorityLevel.MID
    language: JobLanguage = JobLanguage.DE
    description_text: str
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: str = "EUR"


class ATSMatchRequest(BaseModel):
    cv_id: str
    job_id: str


class BulkATSMatchRequest(BaseModel):
    job_id: str
    cv_ids: List[str] = Field(..., description="List of CV IDs to score against this JD")


class CandidateRanking(BaseModel):
    """Summary row for ranked candidate list."""
    rank: int
    cv_id: str
    candidate_name: Optional[str] = None
    total_score: float
    recommendation: str
    shortlist: bool
    matched_skills_count: int
    missing_required_count: int
    pipeline_stage: PipelineStage = PipelineStage.NEW
    applied_at: str
