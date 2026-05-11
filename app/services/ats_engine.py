"""
app/services/ats_engine.py
===========================
Enterprise-grade ATS matching engine.
Mirrors scoring logic used by Taleo, Workday, SAP SuccessFactors ATS systems.
Multilingual: DE, EN, FR, SV.

Scoring weights (total = 100 pts):
  35% — Skills match (required + preferred)
  20% — Years of experience
  15% — Education level
  15% — Language proficiency
  10% — Soft skills
   5% — Location / availability

Hard requirements (pass/fail before scoring):
  - Minimum years of experience
  - Required work authorisation (DACH / EU / Nordic)
  - Required languages at minimum proficiency
  - Mandatory certifications

Employers supported in mock mode:
  Deloitte, KPMG, Deutsche Bank, Six Group, Accenture, Sparkasse,
  UBS, PwC, EY, Siemens, Bosch, Allianz, Zurich Insurance, SAP SE,
  Handelsbanken, Nordea (SV employers)
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from app.models.ats import (
    ATSMatchResult,
    ATSScoreBreakdown,
    CandidateRanking,
    HardRequirementCheck,
    HardRequirementResult,
    JobRequisition,
    PipelineStage,
)
from app.models.cv import CVExtractionResult
from app.services.multilingual_keywords import (
    CERT_REVERSE,
    MULTILINGUAL_SKILLS,
    SKILL_REVERSE,
    get_all_terms_for_skill,
    normalise_certification,
    normalise_education,
    normalise_skill,
)

# ─────────────────────────────────────────────────────────────────────────────
# Education level hierarchy (higher = better)
# ─────────────────────────────────────────────────────────────────────────────
EDUCATION_RANK = {
    "phd": 4,
    "master": 3,
    "bachelor": 2,
    "vocational": 1,
    None: 0,
}

# Language proficiency hierarchy
LANG_RANK = {
    "native": 7, "c2": 6, "c1": 5, "b2": 4,
    "b1": 3, "a2": 2, "a1": 1, None: 0,
}

# Recommendation thresholds
RECOMMENDATION_THRESHOLDS = {
    "STRONG_MATCH": 80,
    "GOOD_MATCH": 65,
    "POSSIBLE_MATCH": 50,
    "WEAK_MATCH": 35,
}


class ATSEngine:
    """
    Core ATS matching engine.
    Usage:
        engine = ATSEngine()
        result = engine.match(cv, job)
    """

    def __init__(self, confidence_threshold: float = 0.0):
        self.confidence_threshold = confidence_threshold

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def match(self, cv: CVExtractionResult, job: JobRequisition) -> ATSMatchResult:
        """Score a CV against a Job Requisition and return a full ATSMatchResult."""
        now = datetime.now(timezone.utc).isoformat()
        match_id = f"match-{uuid.uuid4().hex[:12]}"

        # 1. Extract candidate skills (normalised canonical keys)
        cv_skills = self._extract_cv_skills(cv)
        cv_certs = self._extract_cv_certifications(cv)
        cv_edu = self._extract_cv_education(cv)
        cv_languages = self._extract_cv_languages(cv)

        # 2. Hard requirement checks (pass/fail)
        hr_checks, auto_rejected, rejection_reason = self._check_hard_requirements(
            cv, job, cv_skills, cv_certs, cv_languages
        )

        if auto_rejected:
            return ATSMatchResult(
                match_id=match_id,
                cv_id=cv.document_id,
                job_id=job.job_id,
                employer=job.employer,
                job_title=job.title,
                matched_at=now,
                total_score=0.0,
                recommendation="NO_MATCH",
                shortlist=False,
                hard_requirements_passed=False,
                hard_requirement_checks=hr_checks,
                auto_rejected=True,
                auto_rejection_reason=rejection_reason,
                improvement_tips=[f"Hard requirement not met: {rejection_reason}"],
                recruiter_summary=(
                    f"Candidate automatically screened out: {rejection_reason}. "
                    f"Does not meet minimum requirements for {job.title} at {job.employer}."
                ),
            )

        # 3. Compute weighted score components
        skills_score, matched, missing_req, missing_pref, bonus = self._score_skills(
            cv_skills, job
        )
        experience_score = self._score_experience(cv, job)
        education_score = self._score_education(cv_edu, job)
        language_score, lang_matches, lang_gaps = self._score_languages(cv_languages, job)
        soft_skills_score = self._score_soft_skills(cv_skills)
        location_score = self._score_location(cv, job)

        # 4. Weighted total
        total = (
            skills_score * 0.35
            + experience_score * 0.20
            + education_score * 0.15
            + language_score * 0.15
            + soft_skills_score * 0.10
            + location_score * 0.05
        )
        total = round(min(total, 100.0), 1)

        # 5. Cert bonus (+2 per matching cert, max +6)
        cert_bonus = min(len([c for c in job.required_certifications if c in cv_certs]) * 2, 6)
        total = round(min(total + cert_bonus, 100.0), 1)

        # 6. Recommendation
        recommendation = self._get_recommendation(total)
        shortlist = total >= 65

        # 7. Breakdown model
        breakdown = ATSScoreBreakdown(
            skills_score=round(skills_score, 1),
            experience_score=round(experience_score, 1),
            education_score=round(education_score, 1),
            language_score=round(language_score, 1),
            soft_skills_score=round(soft_skills_score, 1),
            location_score=round(location_score, 1),
            required_skills_matched=len(matched),
            required_skills_total=len(job.required_skills),
            preferred_skills_matched=len([s for s in job.preferred_skills if s in cv_skills]),
            preferred_skills_total=len(job.preferred_skills),
            certifications_matched=len([c for c in job.required_certifications if c in cv_certs]),
            certifications_required=len(job.required_certifications),
        )

        # 8. Improvement tips
        tips = self._generate_tips(
            missing_req, missing_pref, lang_gaps, cv_edu, job, total
        )

        # 9. Recruiter summary
        summary = self._generate_recruiter_summary(cv, job, total, recommendation, matched, missing_req)

        return ATSMatchResult(
            match_id=match_id,
            cv_id=cv.document_id,
            job_id=job.job_id,
            employer=job.employer,
            job_title=job.title,
            matched_at=now,
            total_score=total,
            recommendation=recommendation,
            shortlist=shortlist,
            hard_requirements_passed=True,
            hard_requirement_checks=hr_checks,
            auto_rejected=False,
            breakdown=breakdown,
            matched_skills=matched,
            missing_required_skills=missing_req,
            missing_preferred_skills=missing_pref,
            bonus_skills=bonus,
            language_matches=lang_matches,
            language_gaps=lang_gaps,
            improvement_tips=tips,
            recruiter_summary=summary,
        )

    def rank_candidates(
        self,
        results: List[ATSMatchResult],
    ) -> List[CandidateRanking]:
        """Sort ATSMatchResults by score descending and return ranked list."""
        sorted_results = sorted(results, key=lambda r: r.total_score, reverse=True)
        rankings = []
        for i, r in enumerate(sorted_results, 1):
            rankings.append(CandidateRanking(
                rank=i,
                cv_id=r.cv_id,
                candidate_name=None,  # PII — set by caller if not masked
                total_score=r.total_score,
                recommendation=r.recommendation,
                shortlist=r.shortlist,
                matched_skills_count=len(r.matched_skills),
                missing_required_count=len(r.missing_required_skills),
                pipeline_stage=PipelineStage.NEW,
                applied_at=r.matched_at,
            ))
        return rankings

    # ─────────────────────────────────────────────────────────────────────────
    # Job description parser
    # ─────────────────────────────────────────────────────────────────────────

    def parse_job_description(self, job: JobRequisition) -> JobRequisition:
        """
        Extract required/preferred skills, education, experience, and language
        requirements from the raw JD text. Populates job fields in-place.
        """
        text = job.description_text.lower()
        tokens = self._tokenise(text)

        # Skills
        found_skills = set()
        for token in tokens:
            canonical = normalise_skill(token)
            if canonical:
                found_skills.add(canonical)

        # Split into required vs preferred based on context
        required_context = self._extract_context(text, [
            "required", "must have", "essential", "erforderlich", "voraussetzung",
            "zwingend", "obligatoire", "requis", "obligatorisk", "krav",
            "you bring", "sie bringen mit", "vous apportez",
        ])
        preferred_context = self._extract_context(text, [
            "preferred", "nice to have", "advantage", "wünschenswert", "von vorteil",
            "souhaité", "un atout", "meriterande", "meritmejterande",
        ])

        required_skills = []
        preferred_skills = []
        for skill in found_skills:
            terms = get_all_terms_for_skill(skill)
            in_required = any(t in required_context for t in terms)
            in_preferred = any(t in preferred_context for t in terms)
            if in_required:
                required_skills.append(skill)
            elif in_preferred:
                preferred_skills.append(skill)
            else:
                required_skills.append(skill)   # default to required

        job.required_skills = list(set(required_skills))
        job.preferred_skills = list(set(preferred_skills))

        # Certifications
        for token in tokens:
            cert = normalise_certification(token)
            if cert and cert not in job.required_certifications:
                job.required_certifications.append(cert)

        # Education
        if not job.required_education:
            for token in tokens:
                edu = normalise_education(token)
                if edu:
                    job.required_education = edu
                    break

        # Experience (look for patterns like "5+ years", "min. 3 Jahre")
        exp_patterns = [
            r"(\d+)\+?\s*(?:years?|jahre?|ans?|år)\s*(?:of\s+)?(?:experience|erfahrung|expérience|erfarenhet)",
            r"(?:minimum|mindestens|minimum|minst)\s+(\d+)\s*(?:years?|jahre?|ans?|år)",
            r"(\d+)[–-](\d+)\s*(?:years?|jahre?|ans?|år)",
        ]
        for pattern in exp_patterns:
            m = re.search(pattern, text)
            if m:
                job.min_years_experience = float(m.group(1))
                if len(m.groups()) >= 2 and m.group(2):
                    job.max_years_experience = float(m.group(2))
                break

        return job

    # ─────────────────────────────────────────────────────────────────────────
    # CV feature extraction
    # ─────────────────────────────────────────────────────────────────────────

    def _extract_cv_skills(self, cv: CVExtractionResult) -> set:
        """Return set of canonical skill keys from CV."""
        skills = set()
        all_skills = []
        if cv.technical_skills:
            all_skills.extend(cv.technical_skills)
        if cv.soft_skills:
            all_skills.extend(cv.soft_skills)
        if cv.all_skills:
            all_skills.extend(cv.all_skills)

        for skill in all_skills:
            tokens = self._tokenise(skill.lower())
            for token in tokens:
                canonical = normalise_skill(token)
                if canonical:
                    skills.add(canonical)
            # Also try the full phrase
            canonical = normalise_skill(skill.lower().strip())
            if canonical:
                skills.add(canonical)

        return skills

    def _extract_cv_certifications(self, cv: CVExtractionResult) -> set:
        certs = set()
        if cv.certifications:
            for cert in cv.certifications:
                canonical = normalise_certification(cert.lower().strip())
                if canonical:
                    certs.add(canonical)
                for token in self._tokenise(cert.lower()):
                    c = normalise_certification(token)
                    if c:
                        certs.add(c)
        return certs

    def _extract_cv_education(self, cv: CVExtractionResult) -> Optional[str]:
        if cv.education:
            for edu in cv.education:
                degree = (edu.get("degree") or "").lower()
                for token in self._tokenise(degree):
                    level = normalise_education(token)
                    if level:
                        return level
                level = normalise_education(degree)
                if level:
                    return level
        return None

    def _extract_cv_languages(self, cv: CVExtractionResult) -> Dict[str, str]:
        """Return {canonical_lang_skill: proficiency_level} dict."""
        langs: Dict[str, str] = {}
        if cv.languages:
            for lang_entry in cv.languages:
                name = (lang_entry.get("language") or "").lower()
                level = (lang_entry.get("proficiency") or "").lower()
                for key in ["german_language", "english_language", "french_language", "swedish_language"]:
                    terms = get_all_terms_for_skill(key)
                    if name in terms or any(t in name for t in terms):
                        langs[key] = level
                        break
        # Also check german_proficiency field
        if cv.german_proficiency and "german_language" not in langs:
            langs["german_language"] = cv.german_proficiency.lower()
        return langs

    # ─────────────────────────────────────────────────────────────────────────
    # Hard requirement checks
    # ─────────────────────────────────────────────────────────────────────────

    def _check_hard_requirements(
        self,
        cv: CVExtractionResult,
        job: JobRequisition,
        cv_skills: set,
        cv_certs: set,
        cv_languages: Dict[str, str],
    ) -> Tuple[List[HardRequirementCheck], bool, Optional[str]]:
        checks = []
        auto_rejected = False
        rejection_reason = None

        # Min experience
        if job.min_years_experience is not None:
            cv_exp = cv.years_of_experience or 0
            if cv_exp >= job.min_years_experience:
                checks.append(HardRequirementCheck(
                    requirement=f"Min {job.min_years_experience:.0f} years experience",
                    result=HardRequirementResult.PASS,
                    detail=f"Candidate has {cv_exp:.1f} years",
                ))
            else:
                checks.append(HardRequirementCheck(
                    requirement=f"Min {job.min_years_experience:.0f} years experience",
                    result=HardRequirementResult.FAIL,
                    detail=f"Candidate has {cv_exp:.1f} years — {job.min_years_experience - cv_exp:.1f} short",
                ))
                auto_rejected = True
                rejection_reason = f"Insufficient experience ({cv_exp:.1f} vs {job.min_years_experience:.0f} required)"

        # Required languages
        for lang_req in job.required_languages:
            lang_key = lang_req.get("language", "")
            min_level = lang_req.get("min_level", "b2").lower()
            candidate_level = cv_languages.get(lang_key, "unknown")
            candidate_rank = LANG_RANK.get(candidate_level, 0)
            required_rank = LANG_RANK.get(min_level, 4)

            if candidate_rank >= required_rank:
                checks.append(HardRequirementCheck(
                    requirement=f"Language: {lang_key} ≥ {min_level.upper()}",
                    result=HardRequirementResult.PASS,
                    detail=f"Candidate level: {candidate_level.upper()}",
                ))
            elif candidate_level == "unknown":
                checks.append(HardRequirementCheck(
                    requirement=f"Language: {lang_key} ≥ {min_level.upper()}",
                    result=HardRequirementResult.UNKNOWN,
                    detail="Language not specified in CV — flagged for manual review",
                ))
            else:
                checks.append(HardRequirementCheck(
                    requirement=f"Language: {lang_key} ≥ {min_level.upper()}",
                    result=HardRequirementResult.FAIL,
                    detail=f"Candidate level {candidate_level.upper()} below required {min_level.upper()}",
                ))
                if not auto_rejected:
                    auto_rejected = True
                    rejection_reason = f"Language requirement not met: {lang_key} requires {min_level.upper()}"

        # Required certifications (hard)
        for cert in job.hard_requirements:
            if cert.field == "required_certification":
                cert_key = cert.value
                if cert_key in cv_certs:
                    checks.append(HardRequirementCheck(
                        requirement=f"Certification: {cert_key}",
                        result=HardRequirementResult.PASS,
                        detail="Found in CV",
                    ))
                else:
                    checks.append(HardRequirementCheck(
                        requirement=f"Certification: {cert_key}",
                        result=HardRequirementResult.FAIL,
                        detail="Not found in CV",
                    ))
                    if not auto_rejected:
                        auto_rejected = True
                        rejection_reason = f"Required certification missing: {cert_key}"

        # Work authorisation
        dach_elig = getattr(cv, "dach_eligibility", None)
        for hr in job.hard_requirements:
            if hr.field == "work_authorization" and hr.value == "EU_EEA_required":
                if dach_elig in ["eu_eea_citizen", "swiss_citizen", "bilateral_agreement"]:
                    checks.append(HardRequirementCheck(
                        requirement="Work authorisation: EU/EEA required",
                        result=HardRequirementResult.PASS,
                        detail=f"Eligibility: {dach_elig}",
                    ))
                elif dach_elig == "unknown":
                    checks.append(HardRequirementCheck(
                        requirement="Work authorisation: EU/EEA required",
                        result=HardRequirementResult.UNKNOWN,
                        detail="Work authorisation unknown — manual review required",
                    ))
                else:
                    checks.append(HardRequirementCheck(
                        requirement="Work authorisation: EU/EEA required",
                        result=HardRequirementResult.FAIL,
                        detail=f"Eligibility: {dach_elig} — may require sponsorship",
                    ))

        return checks, auto_rejected, rejection_reason

    # ─────────────────────────────────────────────────────────────────────────
    # Scoring components
    # ─────────────────────────────────────────────────────────────────────────

    def _score_skills(
        self, cv_skills: set, job: JobRequisition
    ) -> Tuple[float, List[str], List[str], List[str], List[str]]:
        """Returns (score 0-100, matched_req, missing_req, missing_pref, bonus)."""
        req = set(job.required_skills)
        pref = set(job.preferred_skills)
        all_known = set(MULTILINGUAL_SKILLS.keys())

        matched_req = list(req & cv_skills)
        missing_req = list(req - cv_skills)
        matched_pref = list(pref & cv_skills)
        missing_pref = list(pref - cv_skills)
        bonus = list(cv_skills - req - pref)

        # Required skills score (0-80 of this component)
        if req:
            req_score = (len(matched_req) / len(req)) * 80
        else:
            req_score = 80.0

        # Preferred skills score (0-20 of this component)
        if pref:
            pref_score = (len(matched_pref) / len(pref)) * 20
        else:
            pref_score = 20.0

        total_skills_score = min(req_score + pref_score, 100.0)
        return total_skills_score, matched_req, missing_req, missing_pref, bonus

    def _score_experience(self, cv: CVExtractionResult, job: JobRequisition) -> float:
        cv_exp = cv.years_of_experience or 0
        min_req = job.min_years_experience
        max_req = job.max_years_experience

        if min_req is None:
            return 85.0   # No requirement — assume fine

        if cv_exp < min_req:
            # Partial credit if close (within 1 year)
            gap = min_req - cv_exp
            if gap <= 1:
                return 60.0
            return 0.0  # hard fail already caught above

        if max_req and cv_exp > max_req * 1.5:
            # Overqualified — penalise slightly
            return 80.0

        # Score based on how well experience matches
        if cv_exp >= min_req:
            excess = cv_exp - min_req
            score = 85.0 + min(excess * 2, 15.0)   # up to 100 for extra exp
            return min(score, 100.0)

        return 70.0

    def _score_education(self, cv_edu: Optional[str], job: JobRequisition) -> float:
        req_edu = job.required_education
        if not req_edu:
            return 85.0

        candidate_rank = EDUCATION_RANK.get(cv_edu, 0)
        required_rank = EDUCATION_RANK.get(req_edu, 0)

        if candidate_rank >= required_rank:
            bonus = (candidate_rank - required_rank) * 5
            return min(90.0 + bonus, 100.0)
        elif candidate_rank == required_rank - 1:
            return 60.0   # One level below
        else:
            return 30.0   # Two or more levels below

    def _score_languages(
        self, cv_languages: Dict[str, str], job: JobRequisition
    ) -> Tuple[float, List[Dict], List[Dict]]:
        if not job.required_languages:
            return 85.0, [], []

        matches = []
        gaps = []
        scores = []

        for lang_req in job.required_languages:
            lang_key = lang_req.get("language", "")
            min_level = lang_req.get("min_level", "b2").lower()
            weight = float(lang_req.get("weight", 1.0))
            candidate_level = cv_languages.get(lang_key, "unknown")
            candidate_rank = LANG_RANK.get(candidate_level, 0)
            required_rank = LANG_RANK.get(min_level, 4)

            if candidate_level == "unknown":
                scores.append((50.0, weight))
                gaps.append({"language": lang_key, "required": min_level, "candidate": "unknown"})
            elif candidate_rank >= required_rank:
                score = 90.0 + min((candidate_rank - required_rank) * 5, 10.0)
                scores.append((score, weight))
                matches.append({"language": lang_key, "required": min_level, "candidate": candidate_level})
            else:
                score = max(40.0, candidate_rank / required_rank * 80)
                scores.append((score, weight))
                gaps.append({"language": lang_key, "required": min_level, "candidate": candidate_level})

        if not scores:
            return 85.0, matches, gaps

        total_weight = sum(w for _, w in scores)
        weighted_avg = sum(s * w for s, w in scores) / total_weight
        return round(weighted_avg, 1), matches, gaps

    def _score_soft_skills(self, cv_skills: set) -> float:
        soft_skills = {
            "communication", "leadership", "project_management",
            "consulting", "agile",
        }
        matched = cv_skills & soft_skills
        if not matched:
            return 50.0
        return min(60.0 + len(matched) * 10, 100.0)

    def _score_location(self, cv: CVExtractionResult, job: JobRequisition) -> float:
        if job.remote_possible:
            return 90.0
        if not job.location or not cv.location:
            return 70.0
        # Simple city matching
        jd_loc = job.location.lower()
        cv_loc = (cv.location or "").lower()
        cities = ["berlin", "frankfurt", "münchen", "munich", "hamburg", "zürich",
                  "zurich", "wien", "vienna", "stockholm", "düsseldorf"]
        for city in cities:
            if city in jd_loc and city in cv_loc:
                return 100.0
        # Same country
        country_pairs = [("de", "de"), ("ch", "ch"), ("at", "at"), ("se", "sv")]
        for pair in country_pairs:
            if pair[0] in jd_loc and pair[1] in cv_loc:
                return 80.0
        return 50.0  # Different location, no remote

    # ─────────────────────────────────────────────────────────────────────────
    # Text helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _tokenise(self, text: str) -> List[str]:
        """Split text into overlapping 1-4 word n-grams for keyword matching."""
        words = re.findall(r"[\w\./\-#]+", text.lower())
        tokens = list(words)
        for n in range(2, 5):
            for i in range(len(words) - n + 1):
                tokens.append(" ".join(words[i:i+n]))
        return tokens

    def _extract_context(self, text: str, markers: List[str]) -> str:
        """Extract the text section following any of the given marker phrases."""
        context_parts = []
        for marker in markers:
            idx = text.find(marker.lower())
            if idx != -1:
                context_parts.append(text[idx:idx+500])
        return " ".join(context_parts)

    # ─────────────────────────────────────────────────────────────────────────
    # Recommendation & narrative
    # ─────────────────────────────────────────────────────────────────────────

    def _get_recommendation(self, score: float) -> str:
        if score >= RECOMMENDATION_THRESHOLDS["STRONG_MATCH"]:
            return "STRONG_MATCH"
        elif score >= RECOMMENDATION_THRESHOLDS["GOOD_MATCH"]:
            return "GOOD_MATCH"
        elif score >= RECOMMENDATION_THRESHOLDS["POSSIBLE_MATCH"]:
            return "POSSIBLE_MATCH"
        elif score >= RECOMMENDATION_THRESHOLDS["WEAK_MATCH"]:
            return "WEAK_MATCH"
        return "NO_MATCH"

    def _generate_tips(
        self,
        missing_req: List[str],
        missing_pref: List[str],
        lang_gaps: List[Dict],
        cv_edu: Optional[str],
        job: JobRequisition,
        score: float,
    ) -> List[str]:
        tips = []
        if missing_req:
            top_missing = missing_req[:3]
            tips.append(
                f"Add these required skills to your CV: {', '.join(top_missing)}. "
                f"Use exact terminology from the job description."
            )
        for gap in lang_gaps[:2]:
            lang = gap.get("language", "").replace("_language", "").capitalize()
            required = gap.get("required", "").upper()
            candidate = gap.get("candidate", "").upper()
            if candidate == "UNKNOWN":
                tips.append(
                    f"Explicitly state your {lang} language proficiency level (required: {required})."
                )
            else:
                tips.append(
                    f"Improve {lang} proficiency from {candidate} to {required} — "
                    f"consider Goethe-Institut, Alliance Française, or similar courses."
                )
        if job.required_education and EDUCATION_RANK.get(cv_edu, 0) < EDUCATION_RANK.get(job.required_education, 0):
            tips.append(
                f"This role requires {job.required_education} level education. "
                f"Highlight any equivalent professional experience or in-progress qualifications."
            )
        if missing_pref:
            tips.append(
                f"Preferred skills you could develop: {', '.join(missing_pref[:3])}. "
                f"Even a training course or side project would strengthen your application."
            )
        if score >= 65:
            tips.append(
                "Strong match! Tailor your cover letter to highlight your direct experience "
                f"in {job.department or 'this field'} and quantify your achievements."
            )
        return tips[:5]

    def _generate_recruiter_summary(
        self,
        cv: CVExtractionResult,
        job: JobRequisition,
        score: float,
        recommendation: str,
        matched: List[str],
        missing_req: List[str],
    ) -> str:
        name = cv.full_name or "The candidate"
        exp = f"{cv.years_of_experience:.0f}" if cv.years_of_experience else "unknown"
        match_pct = f"{score:.0f}%"
        rec_label = recommendation.replace("_", " ").title()

        if recommendation in ("STRONG_MATCH", "GOOD_MATCH"):
            action = "Recommend for phone screen."
        elif recommendation == "POSSIBLE_MATCH":
            action = "Consider for phone screen if pipeline is thin."
        else:
            action = "Not recommended without further review."

        top_matched = ", ".join(matched[:4]) if matched else "none identified"
        top_missing = ", ".join(missing_req[:3]) if missing_req else "none"

        return (
            f"{name} scores {match_pct} ATS match for {job.title} at {job.employer} "
            f"({rec_label}). {exp} years of experience. "
            f"Key matched skills: {top_matched}. "
            f"Missing required skills: {top_missing}. "
            f"{action}"
        )
