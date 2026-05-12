"""
app/services/pii_masker.py
============================
PII detection and masking / pseudonymisation.
Used for GDPR Art. 5(1)(e) — storage limitation and
Art. 25 — data protection by design and by default.

PII fields for CVs: name, email, phone, DOB, address, nationality
PII fields for invoices: vendor IBAN, personal tax ID
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# PII field definitions per document type
# ──────────────────────────────────────────────────────────────────────────────
CV_PII_FIELDS = {
    "full_name", "email", "phone", "location", "linkedin_url",
    "date_of_birth", "nationality", "website",
}

INVOICE_PII_FIELDS = {
    "vendor_iban", "vendor_tax_id",
}

# Regex patterns for PII detection in free text
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"(\+?[\d\s\-().]{8,20})")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[\s]?[\dA-Z\s]{4,32}\b")
DATE_RE = re.compile(r"\b\d{1,2}[./\-]\d{1,2}[./\-]\d{2,4}\b")


def _mask_value(value: str, method: str = "asterisk") -> str:
    """Mask a string value."""
    if not value:
        return value
    if method == "asterisk":
        if len(value) <= 4:
            return "*" * len(value)
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
    elif method == "redact":
        return "[REDACTED]"
    elif method == "hash":
        import hashlib
        return "sha256:" + hashlib.sha256(value.encode()).hexdigest()[:16]
    return value


class PIIMasker:
    """
    Applies PII masking to extraction result dicts.
    Supports: asterisk masking, full redaction, pseudonymisation.
    """

    def __init__(self, method: str = "redact"):
        """
        Args:
            method: 'asterisk' | 'redact' | 'hash'
        """
        self.method = method

    def mask_dict(
        self,
        data: Dict[str, Any],
        document_type: str = "cv",
    ) -> Tuple[Dict[str, Any], List[str]]:
        """
        Mask PII fields in an extraction result dict.

        Returns:
            (masked_dict, list_of_masked_field_names)
        """
        pii_fields = CV_PII_FIELDS if document_type == "cv" else INVOICE_PII_FIELDS
        masked_fields = []
        result = {}

        for key, value in data.items():
            if key in pii_fields:
                if isinstance(value, str) and value:
                    result[key] = _mask_value(value, self.method)
                    masked_fields.append(key)
                elif isinstance(value, dict) and value.get("value"):
                    result[key] = {
                        **value,
                        "value": _mask_value(str(value["value"]), self.method),
                    }
                    masked_fields.append(key)
                else:
                    result[key] = value
            elif isinstance(value, dict):
                nested, nested_fields = self.mask_dict(value, document_type)
                result[key] = nested
                masked_fields.extend([f"{key}.{f}" for f in nested_fields])
            elif isinstance(value, list):
                result[key] = [
                    self.mask_dict(item, document_type)[0] if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value

        return result, masked_fields

    def mask_free_text(self, text: str) -> str:
        """
        Mask PII patterns in free text (emails, phones, IBANs, dates).
        Used for recruiter_summary and CV descriptions.
        """
        text = EMAIL_RE.sub("[EMAIL REDACTED]", text)
        text = IBAN_RE.sub("[IBAN REDACTED]", text)
        text = PHONE_RE.sub("[PHONE REDACTED]", text)
        return text

    def detect_pii_in_text(self, text: str) -> Dict[str, List[str]]:
        """
        Detect PII patterns in text. Returns dict of {type: [matches]}.
        Used for audit/reporting purposes.
        """
        return {
            "emails": EMAIL_RE.findall(text),
            "phones": PHONE_RE.findall(text),
            "ibans": IBAN_RE.findall(text),
        }
