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

import io
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
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

# ─────────────────────────────────────────────────────────────────────────────
# Free-form scoring — any company JD + any CV text / PDF upload
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/score", response_model=dict, summary="Score any CV against any job")
async def score_freeform(
    cv_text: str = Form("", description="Paste CV/resume text here"),
    cv_file: Optional[UploadFile] = File(None, description="Upload a PDF or .txt CV"),
    job_id: Optional[str] = Form(None, description="Use an existing job ID from the library"),
    job_text: str = Form("", description="Or paste any job description text"),
    employer: str = Form("Company", description="Employer name (when using job_text)"),
    job_title: str = Form("Open Position", description="Job title (when using job_text)"),
    job_language: str = Form("en", description="JD language: de / en / fr / sv"),
    candidate_name: str = Form("", description="Override candidate name (optional)"),
    blind_mode: bool = Form(False, description="Strip PII from result for bias-free review"),
    settings: Settings = Depends(get_settings),
):
    """
    Score ANY CV against ANY job description.
    - Job: provide job_id (from library) OR paste job_text (any company, any language)
    - CV:  upload a PDF/txt file OR paste cv_text directly
    Returns the full ATS score breakdown identical to enterprise systems
    (Taleo / Workday / SAP SuccessFactors scoring model).
    """

    # ── 1. Resolve Job ────────────────────────────────────────────────────────
    if job_id:
        job = get_job(job_id) or _job_store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found in library")
    elif job_text and job_text.strip():
        from app.models.ats import EmploymentType, JobLanguage, SeniorityLevel
        lang_map = {"de": JobLanguage.DE, "en": JobLanguage.EN, "fr": JobLanguage.FR, "sv": JobLanguage.SV}
        tmp_id = f"JR-CUSTOM-{uuid.uuid4().hex[:8].upper()}"
        job = JobRequisition(
            job_id=tmp_id,
            title=job_title,
            employer=employer,
            description_text=job_text,
            language=lang_map.get(job_language.lower(), JobLanguage.EN),
        )
        job = _ats_engine.parse_job_description(job)
        _job_store[tmp_id] = job          # cache so rankings work
    else:
        raise HTTPException(
            status_code=400,
            detail="Provide either job_id or job_text (paste any job description).",
        )

    # ── 2. Resolve CV text ────────────────────────────────────────────────────
    raw_cv_text = cv_text.strip()

    if cv_file and not raw_cv_text:
        content = await cv_file.read()
        filename = (cv_file.filename or "").lower()

        if filename.endswith(".pdf"):
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    raw_cv_text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            except ImportError:
                try:
                    import PyPDF2
                    reader = PyPDF2.PdfReader(io.BytesIO(content))
                    raw_cv_text = "\n".join(p.extract_text() or "" for p in reader.pages)
                except ImportError:
                    raw_cv_text = content.decode("utf-8", errors="ignore")
        else:
            raw_cv_text = content.decode("utf-8", errors="ignore")

    if not raw_cv_text:
        raise HTTPException(
            status_code=400,
            detail="No CV content found. Please paste CV text or upload a PDF/txt file.",
        )

    # ── 3. Parse CV text → CVExtractionResult ────────────────────────────────
    cv = _ats_engine.parse_cv_text(raw_cv_text, candidate_name=candidate_name)

    # ── 4. Run ATS scoring ────────────────────────────────────────────────────
    result = _ats_engine.match(cv, job)
    _match_store[result.match_id] = result

    # ── 5. Build enriched response ────────────────────────────────────────────
    result_dict = result.model_dump()

    # CV parse summary (what the engine found)
    result_dict["cv_parsed"] = {
        "full_name": cv.full_name if not blind_mode else "*** (blind mode)",
        "years_of_experience": cv.years_of_experience,
        "location": cv.location if not blind_mode else "*** (blind mode)",
        "education_level": cv.education[0].level.value if cv.education else None,
        "skills_extracted": len(cv.all_skills),
        "languages_detected": [
            {
                "language": lang.language,
                "level": lang.proficiency.value if lang.proficiency else "unknown",
                "is_native": lang.is_native,
            }
            for lang in cv.languages
        ],
        "parse_confidence": cv.overall_confidence,
        "requires_review": cv.requires_manual_review,
        "eligibility": cv.dach_work_eligibility_classification.value,
    }

    # Job summary
    result_dict["job_parsed"] = {
        "job_id": job.job_id,
        "title": job.title,
        "employer": job.employer,
        "language": job.language.value,
        "required_skills_count": len(job.required_skills),
        "preferred_skills_count": len(job.preferred_skills),
        "required_skills": job.required_skills,
        "preferred_skills": job.preferred_skills,
        "min_years_experience": job.min_years_experience,
        "required_education": job.required_education,
        "required_languages": job.required_languages,
    }

    return result_dict


@router.post("/fetch-jd", response_model=dict, summary="Fetch job description text from a URL")
async def fetch_jd_from_url(body: dict = Body(...)):
    """
    Attempt to fetch plain text from a job posting URL (LinkedIn, StepStone, XING, etc.).
    Returns extracted text which can be pasted into the score endpoint.
    Note: Some sites block automated fetching — in that case, copy-paste the JD manually.
    """
    url = (body.get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="'url' field required")

    try:
        import httpx
        import re as _re

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
        }
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            html = resp.text

        # Strip scripts / styles / tags
        html = _re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=_re.DOTALL | _re.IGNORECASE)
        html = _re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=_re.DOTALL | _re.IGNORECASE)
        html = _re.sub(r"<[^>]+>", " ", html)
        html = _re.sub(r"&[a-z]{2,6};", " ", html)
        text = _re.sub(r"[ \t]+", " ", html)
        text = _re.sub(r"\n{3,}", "\n\n", text).strip()

        # Return first 6000 chars (enough for any JD)
        return {
            "url": url,
            "text": text[:6000],
            "char_count": len(text),
            "success": True,
            "note": "Paste this text into the job_text field of /api/v1/ats/score",
        }

    except Exception as exc:
        return {
            "url": url,
            "text": "",
            "success": False,
            "error": str(exc),
            "note": "Site blocked automated fetching. Please copy-paste the job description manually.",
        }


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
