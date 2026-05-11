"""
tests/test_cv_extractor.py
============================
Unit tests for CV extraction, ATS scoring, DACH eligibility.
Runs in mock mode — no Azure credentials required.
"""
from __future__ import annotations

import pytest

from app.models.cv import (
    ATSJobMatchScore,
    CVExtractionResult,
    DACHWorkEligibility,
    LanguageProficiency,
    TargetRoleCategory,
)
from app.services.cv_extractor import CVExtractor
from app.services.pii_masker import PIIMasker


@pytest.fixture
def extractor():
    return CVExtractor()


@pytest.fixture
def pii_masker():
    return PIIMasker(method="redact")


# ──────────────────────────────────────────────────────────────────────────────
# Mock CV Extraction
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestMockCVExtraction:
    async def test_extract_returns_result(self, extractor):
        result = await extractor.extract(
            blob_url="mock://cv.pdf",
            document_id="test-cv-001",
            original_filename="lebenslauf.pdf",
        )
        assert isinstance(result, CVExtractionResult)
        assert result.document_id == "test-cv-001"

    async def test_german_engineer_scenario(self):
        from app.mock.mock_cv import MockCVExtractor
        result = await MockCVExtractor().extract(
            document_id="cv-de-eng",
            original_filename="cv_schneider.pdf",
            blob_url="mock://cv_schneider.pdf",
            scenario_index=0,
        )
        assert result.full_name == "Maximilian Schneider"
        assert result.nationality == "German"
        assert result.german_proficiency == LanguageProficiency.NATIVE
        assert result.target_role_category == TargetRoleCategory.ENGINEERING
        assert result.years_of_experience == 8.5
        assert len(result.certifications) >= 1
        assert "Azure" in result.all_skills

    async def test_swiss_finance_scenario(self):
        from app.mock.mock_cv import MockCVExtractor
        result = await MockCVExtractor().extract(
            document_id="cv-ch-fin",
            original_filename="cv_keller.pdf",
            blob_url="mock://cv_keller.pdf",
            scenario_index=1,
        )
        assert result.full_name == "Sophie Keller"
        assert result.dach_work_eligibility_classification == DACHWorkEligibility.SWISS_CITIZEN
        assert result.target_role_category == TargetRoleCategory.FINANCE
        assert "Bloomberg" in result.all_skills

    async def test_non_eu_candidate_work_permit(self):
        from app.mock.mock_cv import MockCVExtractor
        result = await MockCVExtractor().extract(
            document_id="cv-intl",
            original_filename="cv_diallo.pdf",
            blob_url="mock://cv_diallo.pdf",
            scenario_index=2,
        )
        assert result.dach_work_eligibility_classification == DACHWorkEligibility.WORK_PERMIT_REQUIRED
        assert result.dach_work_eligibility_note is not None
        assert "Blue Card" in result.dach_work_eligibility_note or "permit" in result.dach_work_eligibility_note.lower()
        # Eligibility note must include informational disclaimer
        assert "informational" in result.dach_work_eligibility_note.lower() or "counsel" in result.dach_work_eligibility_note.lower()


# ──────────────────────────────────────────────────────────────────────────────
# ATS Scoring
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestATSScoring:
    async def test_ats_score_with_jd(self, extractor):
        jd = """
        We are looking for a Senior Azure Data Scientist.
        Requirements: Python, Azure ML, TensorFlow, PyTorch, SQL, scikit-learn,
        Statistics, Machine Learning, NLP, Azure, Docker.
        """
        result = await extractor.extract(
            blob_url="mock://cv.pdf",
            document_id="cv-ats-test",
            original_filename="cv.pdf",
            job_description=jd,
        )
        assert result.ats_score is not None
        assert isinstance(result.ats_score, ATSJobMatchScore)
        assert 0 <= result.ats_score.score <= 100
        assert isinstance(result.ats_score.matched_keywords, list)
        assert isinstance(result.ats_score.missing_keywords, list)

    async def test_ats_score_breakdown_sums_to_total(self, extractor):
        jd = "Python Azure Docker Kubernetes CI/CD Scrum REST API"
        result = await extractor.extract(
            blob_url="mock://cv.pdf",
            document_id="cv-ats-breakdown",
            original_filename="cv.pdf",
            job_description=jd,
        )
        if result.ats_score:
            breakdown_sum = sum(result.ats_score.score_breakdown.values())
            assert abs(breakdown_sum - result.ats_score.score) < 1.0, (
                f"Score breakdown {breakdown_sum} should match total score {result.ats_score.score}"
            )

    async def test_ats_score_without_jd(self, extractor):
        result = await extractor.extract(
            blob_url="mock://cv.pdf",
            document_id="cv-no-jd",
            original_filename="cv.pdf",
            job_description=None,
        )
        assert result.ats_score is None, "ATS score should be None when no JD provided"

    def test_compute_ats_score_direct(self, extractor):
        from app.mock.mock_cv import MOCK_CVS
        from app.models.cv import CVExtractionResult
        from datetime import datetime, timezone

        mock_data = MOCK_CVS[0]
        cv = CVExtractionResult(
            document_id="test",
            original_filename="cv.pdf",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            all_skills=mock_data["all_skills"],
            technical_skills=mock_data["technical_skills"],
            work_experience=mock_data["work_experience"],
            education=mock_data["education"],
            certifications=mock_data["certifications"],
        )
        jd = "We need Python Azure Docker Kubernetes CI/CD Scrum REST API Terraform DevOps"
        score = extractor._compute_ats_score(cv, jd)
        assert score.score > 0
        assert len(score.matched_keywords) > 0


# ──────────────────────────────────────────────────────────────────────────────
# DACH Work Eligibility Classification
# ──────────────────────────────────────────────────────────────────────────────

class TestDACHEligibility:
    def test_german_national_is_eu(self, extractor):
        from app.models.cv import CVExtractionResult
        from datetime import datetime, timezone
        cv = CVExtractionResult(
            document_id="test", original_filename="cv.pdf",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            nationality="German",
        )
        result = extractor._classify_dach_eligibility(cv)
        assert result.dach_work_eligibility_classification == DACHWorkEligibility.EU_EEA_CITIZEN

    def test_swiss_national_is_swiss(self, extractor):
        from app.models.cv import CVExtractionResult
        from datetime import datetime, timezone
        cv = CVExtractionResult(
            document_id="test", original_filename="cv.pdf",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            nationality="Swiss",
        )
        result = extractor._classify_dach_eligibility(cv)
        assert result.dach_work_eligibility_classification == DACHWorkEligibility.SWISS_CITIZEN

    def test_non_eu_requires_permit(self, extractor):
        from app.models.cv import CVExtractionResult
        from datetime import datetime, timezone
        cv = CVExtractionResult(
            document_id="test", original_filename="cv.pdf",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            nationality="Indian",
        )
        result = extractor._classify_dach_eligibility(cv)
        assert result.dach_work_eligibility_classification == DACHWorkEligibility.WORK_PERMIT_REQUIRED

    def test_unknown_nationality(self, extractor):
        from app.models.cv import CVExtractionResult
        from datetime import datetime, timezone
        cv = CVExtractionResult(
            document_id="test", original_filename="cv.pdf",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
        )
        result = extractor._classify_dach_eligibility(cv)
        assert result.dach_work_eligibility_classification == DACHWorkEligibility.UNKNOWN

    def test_eligibility_note_always_has_disclaimer(self, extractor):
        """Eligibility note must always disclaim legal non-binding nature."""
        from app.models.cv import CVExtractionResult
        from datetime import datetime, timezone
        for nationality in ["German", "Swiss", "Indian", None]:
            cv = CVExtractionResult(
                document_id="test", original_filename="cv.pdf",
                uploaded_at=datetime.now(timezone.utc).isoformat(),
                nationality=nationality,
            )
            result = extractor._classify_dach_eligibility(cv)
            if result.dach_work_eligibility_note:
                note_lower = result.dach_work_eligibility_note.lower()
                assert any(word in note_lower for word in ["informational", "counsel", "verify"]), (
                    f"Eligibility note for '{nationality}' missing disclaimer: {result.dach_work_eligibility_note}"
                )


# ──────────────────────────────────────────────────────────────────────────────
# PII Masking
# ──────────────────────────────────────────────────────────────────────────────

class TestPIIMasker:
    def test_mask_cv_pii_fields(self, pii_masker):
        data = {
            "full_name": "Max Mustermann",
            "email": "max@example.de",
            "phone": "+49 89 123456",
            "location": "München",
            "current_title": "Engineer",   # Should NOT be masked
        }
        masked, fields = pii_masker.mask_dict(data, document_type="cv")
        assert masked["full_name"] == "[REDACTED]"
        assert masked["email"] == "[REDACTED]"
        assert masked["phone"] == "[REDACTED]"
        assert masked["location"] == "[REDACTED]"
        assert masked["current_title"] == "Engineer"  # Non-PII untouched
        assert "full_name" in fields
        assert "current_title" not in fields

    def test_mask_free_text(self, pii_masker):
        text = "Contact: max@example.de or call +49 89 123456. IBAN: DE89370400440532013000"
        masked = pii_masker.mask_free_text(text)
        assert "max@example.de" not in masked
        assert "[EMAIL REDACTED]" in masked or "[PHONE REDACTED]" in masked or "[IBAN REDACTED]" in masked

    def test_detect_pii_in_text(self, pii_masker):
        text = "Email: test@company.ch, Phone: +41 44 123 45 67"
        pii = pii_masker.detect_pii_in_text(text)
        assert "test@company.ch" in pii["emails"]


# ──────────────────────────────────────────────────────────────────────────────
# Improvement Suggestions
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestImprovementSuggestions:
    async def test_suggestions_generated(self, extractor):
        result = await extractor.extract(
            blob_url="mock://cv.pdf",
            document_id="cv-sug",
            original_filename="cv.pdf",
        )
        assert isinstance(result.candidate_improvement_suggestions, list)

    async def test_missing_german_proficiency_suggestion(self, extractor):
        from app.models.cv import CVExtractionResult
        from datetime import datetime, timezone
        cv = CVExtractionResult(
            document_id="test", original_filename="cv.pdf",
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            full_name="Test User",
            email="test@example.com",
            phone="+49 1234",
            location="Berlin",
        )
        result = extractor._generate_improvement_suggestions(cv)
        suggestions_text = " ".join(result.candidate_improvement_suggestions).lower()
        assert "german" in suggestions_text or "deutsch" in suggestions_text
