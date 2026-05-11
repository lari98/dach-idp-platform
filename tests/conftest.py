"""
tests/conftest.py
==================
Shared pytest configuration and fixtures.
Forces APP_MODE=mock so tests never call Azure.
"""
import os
import pytest

# Force mock mode for all tests
os.environ.setdefault("APP_MODE", "mock")
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("USE_SQLITE_FALLBACK", "true")
os.environ.setdefault("SQLITE_PATH", "./data/test_dach_idp.db")


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Minimal valid PDF bytes for upload tests."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f\n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n%%EOF\n"
    )
