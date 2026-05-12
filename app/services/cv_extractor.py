"""
app/services/cv_extractor.py
==============================
CV/Resume extraction service.
Routes to Azure AI Document Intelligence (live) or mock (demo).

Features:
  - Structured field extraction (personal, experience, education, skills)
  - ATS keyword scoring against a provided job description
  - DACH work eligibility classification (informational only)
  - Recruiter summary generation
  - Candidate improvement suggestions
  - PII identification for GDPR masking
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import structlog

from app.config import get_settings
from app.models.cv import (
    ATSJobMatchScore,
    CVExtractionResult,
    CertificationEntry,
    DACHWorkEligibility,
    EducationEntry,
    LanguageEntry,
    LanguageProficiency,
    TargetRoleCategory,
    WorkExperienceEntry,
)

log = structlog.get_logger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────────────────────────────────────
# Keyword taxonomy for ATS scoring
# ──────────────────────────────────────────────────────────────────────────────
ROLE_KEYWORD_MAP: Dict[TargetRoleCategory, List[str]] = {
    TargetRoleCategory.ENGINEERING: [
        "Python", "Java", "C++", "Azure", "AWS", "GCP", "Docker", "Kubernetes",
        "REST API", "CI/CD", "Git", "Agile", "Scrum", "SQL", "NoSQL",
        "Microservices", "Terraform", "DevOps", "Linux",
    ],
    TargetRoleCategory.DATA_SCIENCE: [
        "Python", "R", "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
        "scikit-learn", "Pandas", "NumPy", "SQL", "Power BI", "Tableau",
        "Statistics", "Azure ML", "MLflow", "Feature Engineering",
    ],
    TargetRoleCategory.FINANCE: [
        "SAP", "IFRS", "HGB", "Excel", "VBA", "Bloomberg", "Risk Management",
        "Financial Modelling", "Controlling", "DATEV", "Buchhaltung",
        "Rechnungswesen", "Treasury", "Compliance", "Audit",
    ],
    TargetRoleCategory.CONSULTING: [
        "Project Management", "Stakeholder Management", "PowerPoint",
        "Business Analysis", "Change Management", "PRINCE2", "PMP",
        "Workshop Facilitation", "Client Management", "Strategy",
    ],
    TargetRoleCategory.HR: [
        "Recruiting", "Talent Acquisition", "Personalentwicklung", "SAP HR",
        "Workday", "HRIS", "Employer Branding", "Onboarding",
        "Labour Law", "Arbeitsrecht", "Performance Management",
    ],
}

# EU/EEA nationalities for eligibility classification
EU_EEA_NATIONALITIES = {
    "german", "deutsch", "austrian", "österreichisch", "french", "französisch",
    "italian", "italienisch", "spanish", "polish", "dutch", "belgian",
    "swedish", "danish", "norwegian", "finnish", "czech", "slovak",
    "hungarian", "romanian", "bulgarian", "croatian", "greek",
    "portuguese", "irish", "luxembourgish", "slovenian", "estonian",
    "latvian", "lithuanian", "maltese", "cypriot",
}

SWISS_NATIONALITIES = {"swiss", "schweizerisch", "schweizer", "suisse"}


class CVExtractor:
    """
    Orchestrates CV extraction, ATS scoring, and recruiter intelligence.
    """

    def __init__(self):
        self.settings = settings
        self._azure_client = None

    def _get_azure_client(self):
        if self._azure_client is None:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential
            self._azure_client = DocumentAnalysisClient(
                endpoint=self.settings.azure_doc_intel_endpoint,
                credential=AzureKeyCredential(self.settings.azure_doc_intel_key),
            )
        return self._azure_client

    async def extract(
        self,
        blob_url: str,
        document_id: str,
        original_filename: str,
        job_description: Optional[str] = None,
        consent_id: Optional[str] = None,
    ) -> CVExtractionResult:
        """
        Main extraction entry point.

        Args:
            blob_url: Azure Blob URL of the uploaded CV PDF
            document_id: Internal document ID
            original_filename: Original file name
            job_description: Optional JD text for ATS scoring
            consent_id: Linked GDPR consent record ID

        Returns:
            CVExtractionResult with all structured fields
        """
        log.info("cv_extraction_start", document_id=document_id, mode=self.settings.app_mode)

        if self.settings.is_mock_mode:
            from app.mock.mock_cv import MockCVExtractor
            result = await MockCVExtractor().extract(
                document_id=document_id,
                original_filename=original_filename,
                blob_url=blob_url,
            )
        else:
            result = await self._extract_live(
                blob_url=blob_url,
                document_id=document_id,
                original_filename=original_filename,
            )

        # ── Post-processing ────────────────────────────────────────────
        result.consent_id = consent_id
        result = self._classify_role(result)
        result = self._calculate_experience(result)
        result = self._classify_dach_eligibility(result)
        result = self._apply_confidence_flags(result)

        if job_description:
            result.ats_score = self._compute_ats_score(result, job_description)

        result = self._generate_recruiter_summary(result)
        result = self._generate_improvement_suggestions(result)
        result = self._set_retention(result)

        log.info(
            "cv_extraction_complete",
            document_id=document_id,
            overall_confidence=result.overall_confidence,
            ats_score=result.ats_score.score if result.ats_score else None,
        )
        return result

    async def _extract_live(
        self,
        blob_url: str,
        document_id: str,
        original_filename: str,
    ) -> CVExtractionResult:
        """
        Call Azure AI Document Intelligence.
        Uses prebuilt-document for general layout extraction.
        For best results, train a custom model on DACH CVs.
        """
        client = self._get_azure_client()
        poller = client.begin_analyze_document_from_url(
            model_id=self.settings.azure_cv_model_id,
            document_url=blob_url,
        )
        azure_result = poller.result()
        return self._map_azure_cv_result(azure_result, document_id, blob_url, original_filename)

    def _map_azure_cv_result(self, azure_result, document_id, blob_url, original_filename) -> CVExtractionResult:
        """
        Map Azure layout result to CVExtractionResult.
        Azure prebuilt-document gives paragraphs/tables — we parse structured sections.
        For production, use a custom trained model for better accuracy.
        """
        full_text = ""
        if azure_result.pages:
            for page in azure_result.pages:
                for line in (page.lines or []):
                    full_text += line.content + "\n"

        return self._parse_cv_text(
            text=full_text,
            document_id=document_id,
            blob_url=blob_url,
            original_filename=original_filename,
            overall_confidence=0.75,  # Document-level confidence for text extraction
        )

    def _parse_cv_text(
        self,
        text: str,
        document_id: str,
        blob_url: str,
        original_filename: str,
        overall_confidence: float = 0.75,
    ) -> CVExtractionResult:
        """
        Heuristic text parser for CV fields.
        Production enhancement: use spaCy NER + custom Azure model.
        """
        lines = [l.strip() for l in text.split("\n") if l.strip()]

        # Simple email/phone extraction
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", text, re.IGNORECASE)
        phone_match = re.search(r"(\+?[\d\s\-().]{7,20})", text)

        return CVExtractionResult(
            document_id=document_id,
            blob_url=blob_url,
            original_filename=original_filename,
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            full_name=lines[0] if lines else None,
            email=email_match.group(0) if email_match else None,
            phone=phone_match.group(0) if phone_match else None,
            overall_confidence=overall_confidence,
        )

    def _classify_role(self, result: CVExtractionResult) -> CVExtractionResult:
        """Infer target role category from skills."""
        if result.target_role_category:
            return result
        all_skills_lower = {s.lower() for s in result.all_skills + result.technical_skills}
        scores = {}
        for category, keywords in ROLE_KEYWORD_MAP.items():
            matches = sum(1 for kw in keywords if kw.lower() in all_skills_lower)
            scores[category] = matches
        if scores:
            best = max(scores, key=scores.get)
            if scores[best] > 0:
                result.target_role_category = best
        return result

    def _calculate_experience(self, result: CVExtractionResult) -> CVExtractionResult:
        """Calculate total years of professional experience."""
        if result.years_of_experience is not None:
            return result
        total_months = 0
        for exp in result.work_experience:
            if exp.duration_months:
                total_months += exp.duration_months
        if total_months > 0:
            result.years_of_experience = round(total_months / 12, 1)
        return result

    def _classify_dach_eligibility(self, result: CVExtractionResult) -> CVExtractionResult:
        """
        Informational work eligibility classification based on stated nationality.
        NOT a legal determination. Always verify with HR/immigration counsel.
        """
        nat = (result.nationality or "").lower()
        loc = (result.location or "").lower()

        if any(n in nat for n in SWISS_NATIONALITIES):
            result.dach_work_eligibility_classification = DACHWorkEligibility.SWISS_CITIZEN
            result.dach_work_eligibility_note = (
                "Candidate states Swiss nationality. Swiss citizens may work in CH without restriction "
                "and benefit from the CH-EU bilateral agreement for DE/AT. "
                "NOTE: Informational only — verify with qualified immigration counsel."
            )
        elif any(n in nat for n in EU_EEA_NATIONALITIES):
            result.dach_work_eligibility_classification = DACHWorkEligibility.EU_EEA_CITIZEN
            result.dach_work_eligibility_note = (
                "Candidate states EU/EEA nationality. Likely eligible to work in DE/AT/CH "
                "under freedom of movement provisions. Verify current permit requirements for CH. "
                "NOTE: Informational only — verify with qualified immigration counsel."
            )
        elif nat:
            result.dach_work_eligibility_classification = DACHWorkEligibility.WORK_PERMIT_REQUIRED
            result.dach_work_eligibility_note = (
                f"Candidate states non-EU/EEA nationality ({result.nationality}). "
                "A work permit is likely required for employment in DE/AT/CH. "
                "Highly qualified candidates may be eligible for the EU Blue Card (DE/AT). "
                "NOTE: Informational only — always verify with qualified immigration counsel."
            )
        else:
            result.dach_work_eligibility_classification = DACHWorkEligibility.UNKNOWN
            result.dach_work_eligibility_note = (
                "Nationality not stated in CV. Work eligibility cannot be classified. "
                "Please verify directly with the candidate and qualified immigration counsel."
            )
        return result

    def _compute_ats_score(
        self, result: CVExtractionResult, job_description: str
    ) -> ATSJobMatchScore:
        """
        ATS-style keyword matching score (0-100).
        Breakdown: skills 40%, experience keywords 30%, education 20%, certifications 10%.
        """
        jd_lower = job_description.lower()
        all_skills = [s.lower() for s in result.all_skills]

        # Extract meaningful keywords from JD (simple tokenisation)
        jd_words = set(re.findall(r"\b[A-Za-z][A-Za-z+.#]{2,}\b", job_description))
        jd_words_lower = {w.lower() for w in jd_words}

        matched = [s for s in result.all_skills if s.lower() in jd_words_lower]
        missing = [w for w in jd_words if w.lower() not in all_skills and len(w) > 4][:20]

        # Skill score (40%)
        skill_score = min(40.0, (len(matched) / max(len(result.all_skills), 1)) * 40)

        # Experience keyword score (30%)
        exp_keywords_matched = 0
        for exp in result.work_experience:
            desc = (exp.description or "").lower()
            exp_keywords_matched += sum(1 for w in jd_words_lower if w in desc)
        exp_score = min(30.0, exp_keywords_matched * 2)

        # Education score (20%) — degree level matters
        edu_score = 0.0
        if result.education:
            highest = result.education[0]
            level_str = str(highest.level or "").lower()
            if "phd" in level_str or "doktor" in level_str:
                edu_score = 20.0
            elif "master" in level_str or "diplom" in level_str or "mba" in level_str:
                edu_score = 18.0
            elif "bachelor" in level_str:
                edu_score = 14.0
            elif "fachhoch" in level_str or "ausbildung" in level_str:
                edu_score = 10.0

        # Certification score (10%)
        cert_score = min(10.0, len(result.certifications) * 3.0)

        total = skill_score + exp_score + edu_score + cert_score

        return ATSJobMatchScore(
            score=round(total, 1),
            matched_keywords=matched[:20],
            missing_keywords=missing[:20],
            matched_skills=matched,
            missing_skills=missing[:10],
            score_breakdown={
                "skills": round(skill_score, 1),
                "experience": round(exp_score, 1),
                "education": round(edu_score, 1),
                "certifications": round(cert_score, 1),
            },
            job_description_used=job_description[:200] + "..." if len(job_description) > 200 else job_description,
        )

    def _generate_recruiter_summary(self, result: CVExtractionResult) -> CVExtractionResult:
        """Generate a concise ATS-style recruiter summary."""
        name = result.full_name or "Candidate"
        yoe = f"{result.years_of_experience:.0f}" if result.years_of_experience else "Several"
        role = str(result.target_role_category or "professional").replace("_", " ").title()
        location = result.location or "location not stated"
        top_skills = ", ".join(result.all_skills[:5]) if result.all_skills else "not extracted"

        german_note = ""
        if result.german_proficiency:
            german_note = f" German proficiency: {result.german_proficiency.value}."

        result.recruiter_summary = (
            f"{name} is a {yoe}-year {role} professional based in {location}. "
            f"Key skills include: {top_skills}.{german_note} "
            f"Work eligibility classification: {result.dach_work_eligibility_classification.value}. "
            f"ATS score: {result.ats_score.score:.0f}/100." if result.ats_score else ""
        )
        return result

    def _generate_improvement_suggestions(self, result: CVExtractionResult) -> CVExtractionResult:
        """Generate actionable CV improvement suggestions for the DACH market."""
        suggestions = []

        if not result.full_name:
            suggestions.append("Add your full name prominently at the top of the CV.")
        if not result.email:
            suggestions.append("Include a professional email address (avoid informal addresses for DE/CH/AT market).")
        if not result.phone:
            suggestions.append("Add a phone number with international prefix (e.g. +49, +43, +41).")
        if not result.location:
            suggestions.append("State your current city and country — DACH employers often filter by location.")
        if not result.german_proficiency:
            suggestions.append(
                "Explicitly state your German language level (e.g. C1 Fließend / B2 Gute Kenntnisse) — "
                "critical for most DACH positions."
            )
        if not result.certifications:
            suggestions.append(
                "Consider adding relevant certifications (Azure AI-102, PMP, SAP, etc.) — "
                "highly valued in DACH consulting and banking sectors."
            )
        if len(result.work_experience) < 1:
            suggestions.append("Ensure work experience entries include company name, title, dates, and key achievements.")
        if not result.education:
            suggestions.append("Add education details including degree, institution, and graduation year.")
        if result.ats_score and result.ats_score.score < 60 and result.ats_score.missing_keywords:
            top_missing = result.ats_score.missing_keywords[:5]
            suggestions.append(
                f"Your CV is missing key skills from the job description: {', '.join(top_missing)}. "
                "Add these if applicable to your background."
            )

        result.candidate_improvement_suggestions = suggestions
        return result

    def _apply_confidence_flags(self, result: CVExtractionResult) -> CVExtractionResult:
        threshold = self.settings.low_confidence_flag_threshold
        low_conf = []
        if result.overall_confidence < threshold:
            low_conf.append("overall_document")
        result.low_confidence_fields = low_conf
        result.requires_manual_review = result.overall_confidence < self.settings.cv_confidence_threshold
        return result

    def _set_retention(self, result: CVExtractionResult) -> CVExtractionResult:
        from datetime import timedelta
        uploaded = datetime.fromisoformat(result.uploaded_at.replace("Z", "+00:00"))
        retention_until = uploaded + timedelta(days=self.settings.blob_retention_days_cv)
        result.retention_until = retention_until.date().isoformat()
        return result
