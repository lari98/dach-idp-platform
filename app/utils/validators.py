"""
app/utils/validators.py
=========================
DACH-specific validation utilities.
  - IBAN validation (DE, AT, CH)
  - VAT ID (USt-IdNr, UID, MWST-Nr)
  - Swiss QR-Bill reference
  - Amount cross-checks
"""
from __future__ import annotations

import re
from typing import Optional, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# IBAN Validator
# ──────────────────────────────────────────────────────────────────────────────

# IBAN lengths per country (ISO 13616)
IBAN_LENGTHS = {
    "DE": 22,  # Germany
    "AT": 20,  # Austria
    "CH": 21,  # Switzerland
    "LI": 21,  # Liechtenstein
}


def _iban_checksum(iban: str) -> bool:
    """
    Validate IBAN checksum using mod-97 algorithm (ISO 7064).
    """
    iban_clean = iban.replace(" ", "").upper()
    rearranged = iban_clean[4:] + iban_clean[:4]
    # Replace letters with digits: A=10, B=11, ..., Z=35
    numeric = "".join(
        str(ord(c) - ord("A") + 10) if c.isalpha() else c for c in rearranged
    )
    return int(numeric) % 97 == 1


class IBANValidator:
    def validate(self, iban: str) -> Tuple[bool, str]:
        """
        Validate an IBAN for DACH countries.
        Returns (is_valid, message).
        """
        if not iban:
            return False, "IBAN is empty."

        clean = iban.replace(" ", "").upper()

        if not re.match(r"^[A-Z]{2}\d{2}[A-Z0-9]+$", clean):
            return False, f"IBAN format invalid: '{iban}'."

        country = clean[:2]
        expected_len = IBAN_LENGTHS.get(country)
        if expected_len and len(clean) != expected_len:
            return False, (
                f"IBAN length {len(clean)} incorrect for {country} "
                f"(expected {expected_len})."
            )

        if not _iban_checksum(clean):
            return False, "IBAN checksum (mod-97) failed."

        return True, "IBAN is valid."

    def format_iban(self, iban: str) -> str:
        """Format IBAN in groups of 4 for display."""
        clean = iban.replace(" ", "").upper()
        return " ".join(clean[i : i + 4] for i in range(0, len(clean), 4))


# ──────────────────────────────────────────────────────────────────────────────
# VAT ID Validator
# ──────────────────────────────────────────────────────────────────────────────

# Patterns for DACH VAT IDs
VAT_PATTERNS = {
    "DE": re.compile(r"^DE\d{9}$"),                          # USt-IdNr.
    "AT": re.compile(r"^ATU\d{8}$"),                         # UID-Nummer
    "CH": re.compile(r"^CHE-?\d{3}\.?\d{3}\.?\d{3}\s*(MWST|MWSt|TVA|IVA)?$"),  # MWST-Nr
}

# German Steuernummer (not USt-IdNr) — state-dependent format
DE_STEUERNUMMER_RE = re.compile(r"^\d{2,3}/\d{3}/\d{4,5}$")


class VATValidator:
    def validate(self, vat_id: str, country: Optional[str] = None) -> Tuple[bool, str]:
        """
        Validate a VAT ID / tax number for DACH countries.
        """
        if not vat_id:
            return False, "VAT ID is empty."

        clean = vat_id.strip().replace(" ", "")

        # Auto-detect country from prefix
        if not country:
            if clean.upper().startswith("DE"):
                country = "DE"
            elif clean.upper().startswith("ATU") or clean.upper().startswith("AT"):
                country = "AT"
            elif clean.upper().startswith("CHE") or clean.upper().startswith("CH"):
                country = "CH"

        if country and country in VAT_PATTERNS:
            pattern = VAT_PATTERNS[country]
            if pattern.match(clean.upper()):
                return True, f"VAT ID valid ({country})."
            # Also check German Steuernummer
            if country == "DE" and DE_STEUERNUMMER_RE.match(clean):
                return True, "German Steuernummer format valid."
            return False, f"VAT ID format invalid for {country}: '{vat_id}'."

        return True, "VAT ID format not validated (unknown country)."


# ──────────────────────────────────────────────────────────────────────────────
# Swiss QR-Bill Reference Validator
# ──────────────────────────────────────────────────────────────────────────────

class QRBillReferenceValidator:
    """
    Validates Swiss QR-Bill reference numbers.
    See: SIX Group QR-Bill standard (2023).
    Two formats: QR-Reference (27 digits) and Creditor Reference (ISO 11649).
    """

    def validate(self, reference: str) -> Tuple[bool, str]:
        clean = reference.replace(" ", "")

        if re.match(r"^\d{27}$", clean):
            # QR-Reference: last digit is mod-10 checksum
            if self._mod10_check(clean):
                return True, "Valid Swiss QR-Reference."
            return False, "QR-Reference mod-10 checksum failed."

        if re.match(r"^RF\d{2}[A-Z0-9]{1,21}$", clean.upper()):
            # ISO 11649 Creditor Reference
            return True, "Valid ISO 11649 Creditor Reference."

        return False, "Reference is not a valid Swiss QR-Bill or ISO 11649 reference."

    @staticmethod
    def _mod10_check(number: str) -> bool:
        """Swiss mod-10 recursive check digit validation."""
        table = [0, 9, 4, 6, 8, 2, 7, 1, 3, 5]
        carry = 0
        for digit in number[:-1]:
            carry = table[(carry + int(digit)) % 10]
        check = (10 - carry) % 10
        return check == int(number[-1])


# ──────────────────────────────────────────────────────────────────────────────
# Amount Validator
# ──────────────────────────────────────────────────────────────────────────────

def validate_invoice_amounts(
    subtotal_net: Optional[float],
    vat_amount: Optional[float],
    total_gross: Optional[float],
    tolerance: float = 0.05,
) -> Tuple[bool, str]:
    """
    Validate that net + VAT ≈ total (within tolerance).
    Returns (is_consistent, message).
    """
    if subtotal_net is None or vat_amount is None or total_gross is None:
        return True, "Cannot validate: missing amount fields."

    expected = subtotal_net + vat_amount
    diff = abs(expected - total_gross)

    if diff <= tolerance:
        return True, "Invoice amounts are consistent."

    return False, (
        f"Amount inconsistency: {subtotal_net:.2f} + {vat_amount:.2f} = {expected:.2f} "
        f"but total is {total_gross:.2f} (diff {diff:.2f} > tolerance {tolerance:.2f})."
    )
