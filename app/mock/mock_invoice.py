"""
app/mock/mock_invoice.py
=========================
Mock invoice extractor — returns realistic DACH invoice data
without requiring Azure credentials.

Includes 4 representative scenarios:
  1. German invoice (EUR, 19% VAT, high confidence)
  2. Swiss invoice (CHF, 8.1% VAT, QR-Bill reference)
  3. Austrian invoice (EUR, 20% VAT)
  4. Low-confidence invoice requiring manual review
"""
from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.models.invoice import (
    Currency,
    DACHCountry,
    FieldWithConfidence,
    InvoiceExtractionResult,
    LineItem,
    ReviewStatus,
    VendorAddress,
)


MOCK_INVOICES = [
    # ── Invoice 1: German EUR invoice, high confidence ──────────────────
    {
        "scenario": "DE_EUR_high_confidence",
        "vendor_name": FieldWithConfidence(value="Müller & Partner GmbH", confidence=0.97),
        "vendor_address": VendorAddress(
            street="Hauptstraße 42",
            city="München",
            postal_code="80331",
            country=DACHCountry.DE,
        ),
        "vendor_tax_id": FieldWithConfidence(value="DE123456789", confidence=0.94),
        "vendor_iban": FieldWithConfidence(value="DE89370400440532013000", confidence=0.96),
        "vendor_bic": FieldWithConfidence(value="COBADEFFXXX", confidence=0.93),
        "invoice_number": FieldWithConfidence(value="RE-2024-00842", confidence=0.98),
        "invoice_date": date(2024, 3, 15),
        "invoice_date_confidence": 0.97,
        "due_date": date(2024, 4, 14),
        "due_date_confidence": 0.95,
        "payment_reference": FieldWithConfidence(value="RE-2024-00842 / Bestellung 5001", confidence=0.91),
        "currency": Currency.EUR,
        "currency_confidence": 0.99,
        "subtotal_net": 1000.00,
        "subtotal_net_confidence": 0.96,
        "vat_amount": 190.00,
        "vat_amount_confidence": 0.95,
        "vat_rate": 19.0,
        "total_gross": 1190.00,
        "total_gross_confidence": 0.97,
        "line_items": [
            LineItem(description="IT-Beratungsleistungen (10h)", quantity=10, unit_price=100.0, total_price=1000.0, vat_rate=19.0, unit="h", confidence=0.94),
        ],
        "language_detected": "de",
        "country_detected": DACHCountry.DE,
        "overall_confidence": 0.96,
        "requires_manual_review": False,
        "review_status": ReviewStatus.AUTO_APPROVED,
    },
    # ── Invoice 2: Swiss CHF invoice, QR-Bill ────────────────────────────
    {
        "scenario": "CH_CHF_qr_bill",
        "vendor_name": FieldWithConfidence(value="Zürich Data Solutions AG", confidence=0.95),
        "vendor_address": VendorAddress(
            street="Bahnhofstrasse 15",
            city="Zürich",
            postal_code="8001",
            country=DACHCountry.CH,
        ),
        "vendor_tax_id": FieldWithConfidence(value="CHE-123.456.789 MWST", confidence=0.92),
        "vendor_iban": FieldWithConfidence(value="CH9300762011623852957", confidence=0.94),
        "vendor_bic": FieldWithConfidence(value="POFICHBEXXX", confidence=0.91),
        "invoice_number": FieldWithConfidence(value="2024-SZ-0099", confidence=0.96),
        "invoice_date": date(2024, 3, 20),
        "invoice_date_confidence": 0.95,
        "due_date": date(2024, 4, 19),
        "due_date_confidence": 0.93,
        "payment_reference": FieldWithConfidence(value="00 00000 00003 13947 14300 09017", confidence=0.88, low_confidence=False),
        "currency": Currency.CHF,
        "currency_confidence": 0.99,
        "subtotal_net": 2500.00,
        "subtotal_net_confidence": 0.94,
        "vat_amount": 202.50,
        "vat_amount_confidence": 0.92,
        "vat_rate": 8.1,
        "total_gross": 2702.50,
        "total_gross_confidence": 0.95,
        "line_items": [
            LineItem(description="Cloud Infrastructure Setup", quantity=1, unit_price=1500.0, total_price=1500.0, vat_rate=8.1, unit="Pauschal", confidence=0.93),
            LineItem(description="Azure Konfiguration (10h)", quantity=10, unit_price=100.0, total_price=1000.0, vat_rate=8.1, unit="h", confidence=0.91),
        ],
        "language_detected": "de",
        "country_detected": DACHCountry.CH,
        "overall_confidence": 0.93,
        "requires_manual_review": False,
        "review_status": ReviewStatus.AUTO_APPROVED,
    },
    # ── Invoice 3: Austrian EUR invoice ──────────────────────────────────
    {
        "scenario": "AT_EUR_standard",
        "vendor_name": FieldWithConfidence(value="Wien Tech Consulting KG", confidence=0.93),
        "vendor_address": VendorAddress(
            street="Kärntner Straße 28",
            city="Wien",
            postal_code="1010",
            country=DACHCountry.AT,
        ),
        "vendor_tax_id": FieldWithConfidence(value="ATU12345678", confidence=0.90),
        "vendor_iban": FieldWithConfidence(value="AT611904300234573201", confidence=0.92),
        "vendor_bic": FieldWithConfidence(value="RLNWATWWGRAZ", confidence=0.89),
        "invoice_number": FieldWithConfidence(value="AR 2024/0317", confidence=0.94),
        "invoice_date": date(2024, 3, 17),
        "invoice_date_confidence": 0.93,
        "due_date": date(2024, 4, 16),
        "due_date_confidence": 0.91,
        "payment_reference": FieldWithConfidence(value="AR 2024/0317 Beratung Q1", confidence=0.87),
        "currency": Currency.EUR,
        "currency_confidence": 0.99,
        "subtotal_net": 3000.00,
        "subtotal_net_confidence": 0.93,
        "vat_amount": 600.00,
        "vat_amount_confidence": 0.91,
        "vat_rate": 20.0,
        "total_gross": 3600.00,
        "total_gross_confidence": 0.94,
        "line_items": [
            LineItem(description="Strategieberatung März 2024", quantity=1, unit_price=3000.0, total_price=3000.0, vat_rate=20.0, unit="Pauschal", confidence=0.90),
        ],
        "language_detected": "de",
        "country_detected": DACHCountry.AT,
        "overall_confidence": 0.91,
        "requires_manual_review": False,
        "review_status": ReviewStatus.AUTO_APPROVED,
    },
    # ── Invoice 4: Low confidence — manual review required ───────────────
    {
        "scenario": "low_confidence_manual_review",
        "vendor_name": FieldWithConfidence(value="Unbekannter Lieferant", confidence=0.42, low_confidence=True),
        "vendor_address": VendorAddress(raw="[poor scan quality]"),
        "vendor_tax_id": FieldWithConfidence(value=None, confidence=0.0),
        "vendor_iban": FieldWithConfidence(value="DE??", confidence=0.35, low_confidence=True),
        "invoice_number": FieldWithConfidence(value="2024-???", confidence=0.51, low_confidence=True),
        "invoice_date": None,
        "invoice_date_confidence": 0.30,
        "due_date": None,
        "due_date_confidence": 0.0,
        "payment_reference": FieldWithConfidence(value=None, confidence=0.0),
        "currency": Currency.EUR,
        "currency_confidence": 0.65,
        "subtotal_net": None,
        "subtotal_net_confidence": 0.0,
        "vat_amount": None,
        "vat_amount_confidence": 0.0,
        "vat_rate": None,
        "total_gross": 450.00,
        "total_gross_confidence": 0.55,
        "line_items": [],
        "language_detected": "de",
        "country_detected": DACHCountry.DE,
        "overall_confidence": 0.44,
        "requires_manual_review": True,
        "review_status": ReviewStatus.MANUAL_REVIEW,
        "low_confidence_fields": ["vendor_name", "vendor_iban", "invoice_number", "invoice_date", "total_gross"],
        "validation_warnings": [
            "Multiple critical fields have low confidence — document may be a poor scan.",
            "IBAN appears malformed. Manual verification required.",
        ],
    },
]


class MockInvoiceExtractor:
    """Returns realistic mock invoice data for demo/testing without Azure."""

    async def extract(
        self,
        document_id: str,
        original_filename: str,
        blob_url: str,
        scenario_index: Optional[int] = None,
    ) -> InvoiceExtractionResult:
        """
        Return a mock extraction result.
        Cycles through 4 scenarios based on document_id hash,
        or uses scenario_index if provided.
        """
        if scenario_index is not None:
            data = MOCK_INVOICES[scenario_index % len(MOCK_INVOICES)]
        else:
            # Deterministic scenario selection based on doc ID
            idx = hash(document_id) % len(MOCK_INVOICES)
            data = MOCK_INVOICES[idx]

        now = datetime.now(timezone.utc).isoformat()

        return InvoiceExtractionResult(
            document_id=document_id,
            blob_url=blob_url,
            original_filename=original_filename,
            uploaded_at=now,
            language_detected=data.get("language_detected"),
            country_detected=data.get("country_detected"),
            vendor_name=data.get("vendor_name", FieldWithConfidence()),
            vendor_address=data.get("vendor_address"),
            vendor_tax_id=data.get("vendor_tax_id", FieldWithConfidence()),
            vendor_iban=data.get("vendor_iban", FieldWithConfidence()),
            vendor_bic=data.get("vendor_bic", FieldWithConfidence()),
            invoice_number=data.get("invoice_number", FieldWithConfidence()),
            invoice_date=data.get("invoice_date"),
            invoice_date_confidence=data.get("invoice_date_confidence", 0.0),
            due_date=data.get("due_date"),
            due_date_confidence=data.get("due_date_confidence", 0.0),
            payment_reference=data.get("payment_reference", FieldWithConfidence()),
            currency=data.get("currency", Currency.EUR),
            currency_confidence=data.get("currency_confidence", 0.0),
            subtotal_net=data.get("subtotal_net"),
            subtotal_net_confidence=data.get("subtotal_net_confidence", 0.0),
            vat_amount=data.get("vat_amount"),
            vat_amount_confidence=data.get("vat_amount_confidence", 0.0),
            vat_rate=data.get("vat_rate"),
            total_gross=data.get("total_gross"),
            total_gross_confidence=data.get("total_gross_confidence", 0.0),
            line_items=data.get("line_items", []),
            overall_confidence=data.get("overall_confidence", 0.0),
            low_confidence_fields=data.get("low_confidence_fields", []),
            requires_manual_review=data.get("requires_manual_review", False),
            review_status=data.get("review_status", ReviewStatus.AUTO_APPROVED),
            validation_warnings=data.get("validation_warnings", []),
            validation_errors=data.get("validation_errors", []),
        )
