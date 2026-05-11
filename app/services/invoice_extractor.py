"""
app/services/invoice_extractor.py
===================================
Invoice extraction service.
Routes to Azure AI Document Intelligence (live mode)
or mock extractor (demo/mock mode).

Azure AI-102 skill alignment:
  - Uses prebuilt-invoice model
  - Confidence scoring per field
  - Multi-language support: DE, EN, FR, IT
  - DACH-specific: EUR/CHF, IBAN validation, VAT rates
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import List, Optional

import structlog

from app.config import AppMode, get_settings
from app.models.invoice import (
    Currency,
    DACHCountry,
    FieldWithConfidence,
    InvoiceExtractionResult,
    LineItem,
    ReviewStatus,
    VendorAddress,
)
from app.services.pii_masker import PIIMasker
from app.utils.validators import IBANValidator, VATValidator

log = structlog.get_logger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────────────────────────────────────
# DACH VAT reference rates (for validation)
# ──────────────────────────────────────────────────────────────────────────────
DACH_VAT_RATES = {
    "DE": [19.0, 7.0, 0.0],        # Standard, reduced, zero
    "AT": [20.0, 10.0, 13.0, 0.0], # Standard, reduced, special, zero
    "CH": [8.1, 2.6, 3.8, 0.0],    # Standard (2024), reduced, hotel, zero
}


class InvoiceExtractor:
    """
    Orchestrates invoice extraction end-to-end.
    Supports LIVE (Azure) and MOCK modes transparently.
    """

    def __init__(self):
        self.settings = settings
        self.iban_validator = IBANValidator()
        self.vat_validator = VATValidator()
        self.pii_masker = PIIMasker()
        self._azure_client = None

    def _get_azure_client(self):
        """Lazy-load Azure Document Intelligence client."""
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
        consent_id: Optional[str] = None,
    ) -> InvoiceExtractionResult:
        """
        Main entry point. Dispatches to live or mock extractor.

        Args:
            blob_url: Azure Blob URL of the uploaded PDF
            document_id: Internal document ID
            original_filename: Original file name
            consent_id: Linked GDPR consent record ID

        Returns:
            InvoiceExtractionResult with all fields and confidence scores
        """
        log.info("invoice_extraction_start", document_id=document_id, mode=self.settings.app_mode)

        if self.settings.is_mock_mode:
            from app.mock.mock_invoice import MockInvoiceExtractor
            result = await MockInvoiceExtractor().extract(
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

        # ── Post-processing (same for both modes) ──────────────────────
        result.consent_id = consent_id
        result = self._apply_confidence_flags(result)
        result = self._validate_financial_fields(result)
        result = self._set_retention(result)

        log.info(
            "invoice_extraction_complete",
            document_id=document_id,
            overall_confidence=result.overall_confidence,
            requires_review=result.requires_manual_review,
        )
        return result

    async def _extract_live(
        self,
        blob_url: str,
        document_id: str,
        original_filename: str,
    ) -> InvoiceExtractionResult:
        """Call Azure AI Document Intelligence prebuilt-invoice model."""
        client = self._get_azure_client()

        log.info("calling_azure_doc_intel", model=self.settings.azure_invoice_model_id)
        poller = client.begin_analyze_document_from_url(
            model_id=self.settings.azure_invoice_model_id,
            document_url=blob_url,
        )
        azure_result = poller.result()

        return self._map_azure_result(
            azure_result=azure_result,
            document_id=document_id,
            blob_url=blob_url,
            original_filename=original_filename,
        )

    def _map_azure_result(
        self,
        azure_result,
        document_id: str,
        blob_url: str,
        original_filename: str,
    ) -> InvoiceExtractionResult:
        """
        Map raw Azure Document Intelligence result to our InvoiceExtractionResult.
        Field mapping based on Azure prebuilt-invoice schema:
        https://learn.microsoft.com/azure/ai-services/document-intelligence/concept-invoice
        """
        doc = azure_result.documents[0] if azure_result.documents else None
        if not doc:
            return InvoiceExtractionResult(
                document_id=document_id,
                blob_url=blob_url,
                original_filename=original_filename,
                uploaded_at=datetime.now(timezone.utc).isoformat(),
                validation_errors=["Azure returned no document result — file may be corrupted or unsupported."],
                requires_manual_review=True,
                review_status=ReviewStatus.MANUAL_REVIEW,
            )

        fields = doc.fields

        def _field(name: str) -> FieldWithConfidence:
            f = fields.get(name)
            if not f:
                return FieldWithConfidence()
            return FieldWithConfidence(
                value=str(f.value) if f.value else f.content,
                confidence=f.confidence or 0.0,
            )

        def _float_field(name: str):
            f = fields.get(name)
            if not f:
                return None, 0.0
            val = f.value.amount if hasattr(f.value, "amount") else f.value
            return (float(val) if val is not None else None), (f.confidence or 0.0)

        def _date_field(name: str):
            f = fields.get(name)
            if not f or not f.value:
                return None, 0.0
            val = f.value
            if isinstance(val, date):
                return val, (f.confidence or 0.0)
            return None, 0.0

        # Currency detection
        currency_raw = _field("CurrencyCode").value or ""
        currency = Currency.EUR
        if "CHF" in currency_raw.upper():
            currency = Currency.CHF
        elif "USD" in currency_raw.upper():
            currency = Currency.USD

        # Total amounts
        total_gross, total_gross_conf = _float_field("InvoiceTotal")
        subtotal_net, subtotal_net_conf = _float_field("SubTotal")
        vat_amount, vat_amount_conf = _float_field("TotalTax")
        invoice_date, invoice_date_conf = _date_field("InvoiceDate")
        due_date, due_date_conf = _date_field("DueDate")

        # Line items
        line_items = []
        items_field = fields.get("Items")
        if items_field and items_field.value:
            for item in items_field.value:
                item_fields = item.value or {}
                qty_f = item_fields.get("Quantity")
                price_f = item_fields.get("UnitPrice")
                total_f = item_fields.get("Amount")
                desc_f = item_fields.get("Description")

                li = LineItem(
                    description=str(desc_f.value) if desc_f and desc_f.value else None,
                    quantity=float(qty_f.value) if qty_f and qty_f.value else None,
                    unit_price=(float(price_f.value.amount) if hasattr(price_f.value, "amount") else None) if price_f and price_f.value else None,
                    total_price=(float(total_f.value.amount) if hasattr(total_f.value, "amount") else None) if total_f and total_f.value else None,
                    confidence=item.confidence or 0.0,
                )
                line_items.append(li)

        # Confidence aggregation
        conf_values = [
            f.confidence for f in [
                _field("VendorName"),
                _field("InvoiceId"),
            ] if f.confidence > 0
        ]
        if total_gross_conf > 0:
            conf_values.append(total_gross_conf)
        overall_conf = sum(conf_values) / len(conf_values) if conf_values else 0.0

        return InvoiceExtractionResult(
            document_id=document_id,
            blob_url=blob_url,
            original_filename=original_filename,
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            vendor_name=_field("VendorName"),
            vendor_address=VendorAddress(raw=_field("VendorAddress").value),
            vendor_tax_id=_field("VendorTaxId"),
            invoice_number=_field("InvoiceId"),
            invoice_date=invoice_date,
            invoice_date_confidence=invoice_date_conf,
            due_date=due_date,
            due_date_confidence=due_date_conf,
            payment_reference=_field("PurchaseOrder"),
            currency=currency,
            currency_confidence=_field("CurrencyCode").confidence,
            subtotal_net=subtotal_net,
            subtotal_net_confidence=subtotal_net_conf,
            vat_amount=vat_amount,
            vat_amount_confidence=vat_amount_conf,
            total_gross=total_gross,
            total_gross_confidence=total_gross_conf,
            line_items=line_items,
            overall_confidence=overall_conf,
        )

    def _apply_confidence_flags(self, result: InvoiceExtractionResult) -> InvoiceExtractionResult:
        """Flag low-confidence fields and set manual review flag."""
        threshold = self.settings.low_confidence_flag_threshold
        low_conf = []

        checks = {
            "vendor_name": result.vendor_name.confidence,
            "invoice_number": result.invoice_number.confidence,
            "invoice_date": result.invoice_date_confidence,
            "total_gross": result.total_gross_confidence,
            "vat_amount": result.vat_amount_confidence,
            "currency": result.currency_confidence,
        }

        for field_name, conf in checks.items():
            if 0 < conf < threshold:
                low_conf.append(field_name)
                # Update low_confidence flag on FieldWithConfidence objects
                field_obj = getattr(result, field_name, None)
                if hasattr(field_obj, "low_confidence"):
                    field_obj.low_confidence = True

        result.low_confidence_fields = low_conf
        result.requires_manual_review = (
            len(low_conf) > 0
            or result.overall_confidence < self.settings.invoice_confidence_threshold
        )

        if result.requires_manual_review:
            result.review_status = ReviewStatus.MANUAL_REVIEW

        return result

    def _validate_financial_fields(self, result: InvoiceExtractionResult) -> InvoiceExtractionResult:
        """Validate IBAN, VAT, and amount consistency."""
        warnings = list(result.validation_warnings)
        errors = list(result.validation_errors)

        # IBAN validation
        if result.vendor_iban.value:
            iban_ok, iban_msg = self.iban_validator.validate(result.vendor_iban.value)
            if not iban_ok:
                warnings.append(f"IBAN validation: {iban_msg}")

        # VAT consistency check
        if (
            result.country_detected
            and result.vat_rate
            and str(result.country_detected.value) in DACH_VAT_RATES
        ):
            valid_rates = DACH_VAT_RATES[str(result.country_detected.value)]
            if result.vat_rate not in valid_rates:
                warnings.append(
                    f"VAT rate {result.vat_rate}% is unusual for {result.country_detected.value}. "
                    f"Expected one of: {valid_rates}"
                )

        # Amount consistency: subtotal + VAT ≈ total
        if result.subtotal_net and result.vat_amount and result.total_gross:
            expected_total = result.subtotal_net + result.vat_amount
            diff = abs(expected_total - result.total_gross)
            if diff > 0.05:  # 5 cent tolerance
                warnings.append(
                    f"Amount inconsistency: net {result.subtotal_net} + VAT {result.vat_amount} "
                    f"= {expected_total:.2f} ≠ total {result.total_gross:.2f} (diff {diff:.2f})"
                )

        result.validation_warnings = warnings
        result.validation_errors = errors
        return result

    def _set_retention(self, result: InvoiceExtractionResult) -> InvoiceExtractionResult:
        """Compute GDPR retention date (HGB §257 = 10 years for invoices in DE)."""
        from datetime import timedelta
        uploaded = datetime.fromisoformat(result.uploaded_at.replace("Z", "+00:00"))
        retention_until = uploaded + timedelta(days=self.settings.blob_retention_days_invoice)
        result.retention_until = retention_until.date().isoformat()
        return result
