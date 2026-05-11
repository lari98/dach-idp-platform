"""
app/api/ats.py
===============
ATS (Applicant Tracking System) API endpoints.
Multilingual: DE, EN, FR, SV.

Endpoints:
  GET  /api/v1/ats/jobs                     — list all active job requisitions
  GET  /api/v1/ats/jobs/{job_id}            — get one job requisition
  POST /api/v1/ats/jobs                     — create a new job requisition
  POST /api/v1/ats/match                    — match one CV against one job
  POST /api/v1/ats/match/bulk              — match multiple CVs against one job
  GET  /api/v1/ats/jobs/{job_id}/rankings  — ranked candidate list for a job
  GET  /api/v1/ats/jobs/{job_id}/stats     — ATS stats for a job (score dist, funnel)
  GET  /api/v1/ats/health                  — ATS engine health check
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database.connection import get_db
from app.mock.mock_cv import MockCVExtractor
from app.mock.mock_jobs import MOCK_JOBS, get_active_jobs, get_job
from app.models.ats import (
    ATSMatchRequest,
    ATSMatchResult,
    BulkATSMatchRequest,
    CandidateRanking,
    JobRequisition,
    JobRequisitionCreate,
)
from app.services.ats_engine import ATSEngine

router = APIRouter(prefix="/api/v1/ats", tags=["ATS"])

# In-memory store for created jobs and match results (mock mode)
_job_store: Dict[str, JobRequisition] = {}
_match_store: Dict[str, ATSMatchResult] = {}

# Singleton ATS engine
_ats_engine = ATSEngine()


def _get_all_jobs() -> List[JobRequisition]:
    """Return mock jobs + any dynamically created jobs."""
    return list(MOCK_JOBS) + list(_job_store.values())


# ─────────────────────────────────────────────────────────────────────────────
# Jobs
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/jobs", response_model=List[dict])
async def list_jobs(
    employer: Optional[str] = Query(None, description="Filter by employer name"),
    language: Optional[str] = Query(None, description="Filter by JD language: de/en/fr/sv"),
    department: Optional[str] = Query(None, description="Filter by department"),
    active_only: bool = Query(True),
    settings: Settings = Depends(get_settings),
):
    """List all job requisitions."""
    jobs = _get_all_jobs()
    if active_only:
        jobs = [j for j in jobs if j.is_active]
    if employer:
        jobs = [j for j in jobs if employer.lower() in j.employer.lower()]
    if language:
        jobs = [j for j in jobs if j.language.value == language.lower()]
    if department:
        jobs = [j for j in jobs if j.department and department.lower() in j.department.value.lower()]

    return [
        {
            "job_id": j.job_id,
            "title": j.title,
            "employer": j.employer,
            "department": j.department.value if j.department else None,
            "location": j.location,
            "language": j.language.value,
            "seniority": j.seniority.value,
            "employment_type": j.employment_type.value,
            "salary_range": f"{j.salary_min:,}–{j.salary_max:,} {j.currency}" if j.salary_min else None,
            "required_skills": j.required_skills,
            "preferred_skills": j.preferred_skills,
            "min_years_experience": j.min_years_experience,
            "required_education": j.required_education,
            "applications_count": j.applications_count,
            "is_active": j.is_active,
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=dict)
async def get_job_detail(job_id: str, settings: Settings = Depends(get_settings)):
    """Get full details of one job requisition."""
    job = get_job(job_id) or _job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job.model_dump()


@router.post("/jobs", response_model=dict, status_code=201)
async def create_job(
    body: JobRequisitionCreate,
    settings: Settings = Depends(get_settings),
):
    """Create a new job requisition. The ATS engine will parse the JD text automatically."""
    job_id = f"JR-{uuid.uuid4().hex[:8].upper()}"
    job = JobRequisition(
        job_id=job_id,
        **body.model_dump(),
    )
    # Auto-parse the JD text
    job = _ats_engine.parse_job_description(job)
    _job_store[job_id] = job
    return {
        "job_id": job_id,
        "message": "Job requisition created and parsed successfully",
        "parsed_required_skills": job.required_skills,
        "parsed_preferred_skills": job.preferred_skills,
        "parsed_min_years_experience": job.min_years_experience,
        "parsed_required_education": job.required_education,
    }


# ─────────────────────────────────────────────────────────────────────────────
# ATS Matching
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/match", response_model=dict)
async def match_cv_to_job(
    body: ATSMatchRequest,
    settings: Settings = Depends(get_settings),
    db: AsyncSession = Depends(get_db),
):
    """
    Run ATS matching for one CV against one job requisition.
    Returns full scoring breakdown, matched/missing skills, and recruiter summary.
    """
    job = get_job(body.job_id) or _job_store.get(body.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {body.job_id} not found")

    # In mock mode, get CV from mock extractor
    if settings.is_mock_mode:
        mock_extractor = MockCVExtractor()
        cv = await mock_extractor.extract(body.cv_id)
    else:
        # Live mode: load from DB
        from app.database.models import CVDocument
        from sqlalchemy import select
        result = await db.execute(
            select(CVDocument).where(CVDocument.id == body.cv_id)
        )
        cv_doc = result.scalar_one_or_none()
        if not cv_doc:
            raise HTTPException(status_code=404, detail=f"CV {body.cv_id} not found")
        # Build a minimal CVExtractionResult from DB record
        from app.models.cv import CVExtractionResult
        cv = CVExtractionResult(
            document_id=cv_doc.id,
            original_filename=cv_doc.original_filename,
            uploaded_at=cv_doc.uploaded_at.isoformat() if cv_doc.uploaded_at else "",
            full_name=cv_doc.full_name,
            years_of_experience=cv_doc.years_of_experience,
            location=cv_doc.location,
            technical_skills=cv_doc.technical_skills_json or [],
            soft_skills=cv_doc.soft_skills_json or [],
            all_skills=cv_doc.all_skills_json or [],
            languages=cv_doc.languages_json or [],
            german_proficiency=cv_doc.german_proficiency,
            dach_eligibility=cv_doc.dach_eligibility,
            education=[],
            certifications=[],
        )

    result = _ats_engine.match(cv, job)
    _match_store[result.match_id] = result
    return result.model_dump()


@router.post("/match/bulk", response_model=dict)
async def bulk_match(
    body: BulkATSMatchRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Match multiple CVs against one job and return ranked candidate list.
    In mock mode, uses all 4 mock CV personas.
    """
    job = get_job(body.job_id) or _job_store.get(body.job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {body.job_id} not found")

    mock_extractor = MockCVExtractor()
    results = []

    cv_ids = body.cv_ids if body.cv_ids else ["cv-mock-0", "cv-mock-1", "cv-mock-2", "cv-mock-3"]

    for cv_id in cv_ids:
        try:
            cv = await mock_extractor.extract(cv_id)
            match_result = _ats_engine.match(cv, job)
            _match_store[match_result.match_id] = match_result
            results.append(match_result)
        except Exception:
            continue

    rankings = _ats_engine.rank_candidates(results)

    return {
        "job_id": body.job_id,
        "job_title": job.title,
        "employer": job.employer,
        "total_processed": len(results),
        "shortlisted": sum(1 for r in results if r.shortlist),
        "auto_rejected": sum(1 for r in results if r.auto_rejected),
        "rankings": [r.model_dump() for r in rankings],
        "score_distribution": _score_distribution(results),
    }


@router.get("/jobs/{job_id}/rankings", response_model=List[dict])
async def get_rankings(job_id: str):
    """Get ranked candidate list for a specific job based on completed matches."""
    job_matches = [m for m in _match_store.values() if m.job_id == job_id]
    if not job_matches:
        raise HTTPException(
            status_code=404,
            detail=f"No ATS matches found for job {job_id}. Run /match or /match/bulk first."
        )
    rankings = _ats_engine.rank_candidates(job_matches)
    return [r.model_dump() for r in rankings]


@router.get("/jobs/{job_id}/stats", response_model=dict)
async def job_stats(job_id: str):
    """ATS statistics for a job: score distribution, recommendation breakdown, skill gap analysis."""
    job = get_job(job_id) or _job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job_matches = [m for m in _match_store.values() if m.job_id == job_id]

    if not job_matches:
        return {
            "job_id": job_id,
            "message": "No matches yet — run /match/bulk to populate",
            "applications_count": job.applications_count,
        }

    all_missing = {}
    for m in job_matches:
        for skill in m.missing_required_skills:
            all_missing[skill] = all_missing.get(skill, 0) + 1

    top_missing = sorted(all_missing.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "job_id": job_id,
        "job_title": job.title,
        "employer": job.employer,
        "total_applicants": len(job_matches),
        "shortlisted": sum(1 for m in job_matches if m.shortlist),
        "auto_rejected": sum(1 for m in job_matches if m.auto_rejected),
        "avg_ats_score": round(sum(m.total_score for m in job_matches) / len(job_matches), 1),
        "score_distribution": _score_distribution(job_matches),
        "recommendation_breakdown": {
            rec: sum(1 for m in job_matches if m.recommendation == rec)
            for rec in ["STRONG_MATCH", "GOOD_MATCH", "POSSIBLE_MATCH", "WEAK_MATCH", "NO_MATCH"]
        },
        "top_missing_skills": [{"skill": s, "count": c} for s, c in top_missing],
        "pipeline_summary": {
            "new": len(job_matches),
            "screened": sum(1 for m in job_matches if m.shortlist),
            "hired": 0,
            "rejected": sum(1 for m in job_matches if m.auto_rejected),
        },
    }


@router.get("/health", response_model=dict)
async def ats_health():
    """ATS engine health check."""
    return {
        "status": "healthy",
        "engine": "ATSEngine v3.0.0",
        "supported_languages": ["de", "en", "fr", "sv"],
        "active_jobs": len([j for j in _get_all_jobs() if j.is_active]),
        "completed_matches": len(_match_store),
        "scoring_weights": {
            "skills": "35%",
            "experience": "20%",
            "education": "15%",
            "languages": "15%",
            "soft_skills": "10%",
            "location": "5%",
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────────────

def _score_distribution(matches: List[ATSMatchResult]) -> dict:
    bands = {"0-20": 0, "21-40": 0, "41-60": 0, "61-80": 0, "81-100": 0}
    for m in matches:
        s = m.total_score
        if s <= 20:
            bands["0-20"] += 1
        elif s <= 40:
            bands["21-40"] += 1
        elif s <= 60:
            bands["41-60"] += 1
        elif s <= 80:
            bands["61-80"] += 1
        else:
            bands["81-100"] += 1
    return bands
