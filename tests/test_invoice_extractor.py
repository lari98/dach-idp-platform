"""
tests/test_invoice_extractor.py
================================
Unit and integration tests for invoice extraction pipeline.
Runs in mock mode — no Azure credentials required.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from app.config import get_settings
from app.models.invoice import Currency, DACHCountry, InvoiceExtractionResult, ReviewStatus
from app.services.invoice_extractor import InvoiceExtractor, DACH_VAT_RATES
from app.utils.validators import IBANValidator, VATValidator, validate_invoice_amounts


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def extractor():
    return InvoiceExtractor()


@pytest.fixture
def iban_validator():
    return IBANValidator()


@pytest.fixture
def vat_validator():
    return VATValidator()


# ──────────────────────────────────────────────────────────────────────────────
# IBAN Validation Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestIBANValidator:
    def test_valid_german_iban(self, iban_validator):
        ok, msg = iban_validator.validate("DE89370400440532013000")
        assert ok, f"Should be valid: {msg}"

    def test_valid_austrian_iban(self, iban_validator):
        ok, msg = iban_validator.validate("AT611904300234573201")
        assert ok, f"Should be valid: {msg}"

    def test_valid_swiss_iban(self, iban_validator):
        ok, msg = iban_validator.validate("CH9300762011623852957")
        assert ok, f"Should be valid: {msg}"

    def test_invalid_iban_wrong_checksum(self, iban_validator):
        ok, msg = iban_validator.validate("DE00370400440532013000")
        assert not ok, "Should be invalid (wrong checksum)"

    def test_invalid_iban_wrong_length(self, iban_validator):
        ok, msg = iban_validator.validate("DE893704004405320")
        assert not ok, "Should be invalid (wrong length)"

    def test_empty_iban(self, iban_validator):
        ok, msg = iban_validator.validate("")
        assert not ok

    def test_iban_with_spaces(self, iban_validator):
        """IBANs with spaces should still validate."""
        ok, msg = iban_validator.validate("DE89 3704 0044 0532 0130 00")
        assert ok, f"Should be valid with spaces: {msg}"

    def test_iban_format_display(self, iban_validator):
        formatted = iban_validator.format_iban("DE89370400440532013000")
        assert formatted == "DE89 3704 0044 0532 0130 00"


# ──────────────────────────────────────────────────────────────────────────────
# VAT Validation Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestVATValidator:
    def test_valid_german_ust_id(self, vat_validator):
        ok, msg = vat_validator.validate("DE123456789")
        assert ok, msg

    def test_valid_austrian_uid(self, vat_validator):
        ok, msg = vat_validator.validate("ATU12345678")
        assert ok, msg

    def test_valid_swiss_mwst(self, vat_validator):
        ok, msg = vat_validator.validate("CHE-123.456.789 MWST")
        assert ok, msg

    def test_invalid_german_vat(self, vat_validator):
        ok, _ = vat_validator.validate("DE12345")  # Too short
        assert not ok

    def test_empty_vat(self, vat_validator):
        ok, _ = vat_validator.validate("")
        assert not ok

    def test_german_steuernummer(self, vat_validator):
        ok, msg = vat_validator.validate("81/815/08150", country="DE")
        assert ok, msg


# ──────────────────────────────────────────────────────────────────────────────
# Amount Validation Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestAmountValidation:
    def test_consistent_amounts(self):
        ok, msg = validate_invoice_amounts(1000.0, 190.0, 1190.0)
        assert ok, msg

    def test_inconsistent_amounts(self):
        ok, msg = validate_invoice_amounts(1000.0, 190.0, 1250.0)  # Wrong total
        assert not ok

    def test_within_tolerance(self):
        ok, _ = validate_invoice_amounts(1000.0, 190.0, 1190.03)  # 3 cent difference
        assert ok, "Should be within tolerance"

    def test_missing_amounts_returns_true(self):
        ok, _ = validate_invoice_amounts(None, 190.0, 1190.0)
        assert ok, "Cannot validate with missing fields — should not fail"

    def test_swiss_vat_calculation(self):
        # CHF: 8.1% VAT
        net = 2500.0
        vat = round(net * 0.081, 2)  # 202.50
        total = net + vat
        ok, msg = validate_invoice_amounts(net, vat, total)
        assert ok, msg


# ──────────────────────────────────────────────────────────────────────────────
# Mock Extraction Tests
# ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestMockInvoiceExtraction:
    async def test_extract_returns_result(self, extractor):
        result = await extractor.extract(
            blob_url="mock://test.pdf",
            document_id="test-inv-001",
            original_filename="test_invoice.pdf",
        )
        assert isinstance(result, InvoiceExtractionResult)
        assert result.document_id == "test-inv-001"
        assert result.original_filename == "test_invoice.pdf"

    async def test_german_invoice_scenario(self):
        from app.mock.mock_invoice import MockInvoiceExtractor
        extractor = MockInvoiceExtractor()
        result = await extractor.extract(
            document_id="test-de",
            original_filename="rechnung_de.pdf",
            blob_url="mock://rechnung_de.pdf",
            scenario_index=0,  # DE EUR high confidence
        )
        assert result.currency == Currency.EUR
        assert result.country_detected == DACHCountry.DE
        assert result.total_gross == 1190.00
        assert result.vat_rate == 19.0
        assert result.overall_confidence >= 0.90
        assert result.requires_manual_review is False
        assert result.review_status == ReviewStatus.AUTO_APPROVED

    async def test_swiss_invoice_scenario(self):
        from app.mock.mock_invoice import MockInvoiceExtractor
        extractor = MockInvoiceExtractor()
        result = await extractor.extract(
            document_id="test-ch",
            original_filename="rechnung_ch.pdf",
            blob_url="mock://rechnung_ch.pdf",
            scenario_index=1,  # CH CHF QR-Bill
        )
        assert result.currency == Currency.CHF
        assert result.country_detected == DACHCountry.CH
        assert result.vat_rate == 8.1
        assert result.total_gross == 2702.50

    async def test_low_confidence_scenario_triggers_review(self):
        from app.mock.mock_invoice import MockInvoiceExtractor
        extractor = MockInvoiceExtractor()
        result = await extractor.extract(
            document_id="test-low",
            original_filename="bad_scan.pdf",
            blob_url="mock://bad_scan.pdf",
            scenario_index=3,  # Low confidence
        )
        assert result.requires_manual_review is True
        assert result.review_status == ReviewStatus.MANUAL_REVIEW
        assert len(result.low_confidence_fields) > 0
        assert result.overall_confidence < 0.60

    async def test_confidence_flagging(self, extractor):
        result = await extractor.extract(
            blob_url="mock://test.pdf",
            document_id="test-conf",
            original_filename="test.pdf",
        )
        # Post-processing should set low_confidence fields
        assert isinstance(result.low_confidence_fields, list)
        assert isinstance(result.requires_manual_review, bool)

    async def test_retention_date_set(self, extractor):
        result = await extractor.extract(
            blob_url="mock://test.pdf",
            document_id="test-ret",
            original_filename="test.pdf",
        )
        assert result.retention_until is not None
        # Invoice retention should be approx 7 years (2555 days)
        from datetime import date, timedelta
        uploaded = date.today()
        expected_approx = (uploaded + timedelta(days=2555)).isoformat()[:4]  # Year
        assert result.retention_until[:4] >= expected_approx[:4]

    async def test_consent_id_linked(self, extractor):
        result = await extractor.extract(
            blob_url="mock://test.pdf",
            document_id="test-cns",
            original_filename="test.pdf",
            consent_id="cns-abc123",
        )
        assert result.consent_id == "cns-abc123"


# ──────────────────────────────────────────────────────────────────────────────
# DACH VAT Rate Reference Tests
# ──────────────────────────────────────────────────────────────────────────────

class TestDACHVATRates:
    def test_german_vat_rates_defined(self):
        assert "DE" in DACH_VAT_RATES
        assert 19.0 in DACH_VAT_RATES["DE"]
        assert 7.0 in DACH_VAT_RATES["DE"]

    def test_swiss_vat_rates_defined(self):
        assert "CH" in DACH_VAT_RATES
        assert 8.1 in DACH_VAT_RATES["CH"]
        assert 2.6 in DACH_VAT_RATES["CH"]

    def test_austrian_vat_rates_defined(self):
        assert "AT" in DACH_VAT_RATES
        assert 20.0 in DACH_VAT_RATES["AT"]
        assert 10.0 in DACH_VAT_RATES["AT"]
