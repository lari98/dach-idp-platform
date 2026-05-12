"""
app/config.py
=============
Centralised configuration using Pydantic Settings.
Reads from environment variables / .env file.
Supports LIVE (Azure) and MOCK (demo) modes.
"""
from __future__ import annotations

import os
from enum import Enum
from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppMode(str, Enum):
    LIVE = "live"
    MOCK = "mock"


class AppEnv(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────
    app_mode: AppMode = AppMode.MOCK
    app_env: AppEnv = AppEnv.DEVELOPMENT
    app_port: int = 8000
    app_host: str = "0.0.0.0"
    log_level: str = "INFO"
    secret_key: str = "change-me-to-a-secure-random-string-min-32-chars"
    app_version: str = "1.0.0"

    # ── Azure Document Intelligence ───────────────────────────
    azure_doc_intel_endpoint: Optional[str] = None
    azure_doc_intel_key: Optional[str] = None
    azure_invoice_model_id: str = "prebuilt-invoice"
    azure_cv_model_id: str = "prebuilt-document"

    # ── Azure Blob Storage ────────────────────────────────────
    azure_storage_account_name: Optional[str] = None
    azure_storage_connection_string: Optional[str] = None
    azure_storage_container_invoices: str = "invoices"
    azure_storage_container_cvs: str = "cvs"
    azure_storage_container_audit: str = "audit-exports"
    blob_retention_days_invoice: int = 2555   # 7 years (HGB §257)
    blob_retention_days_cv: int = 365

    # ── Azure Key Vault ───────────────────────────────────────
    azure_keyvault_url: Optional[str] = None
    use_keyvault: bool = False

    # ── Azure SQL ─────────────────────────────────────────────
    azure_sql_server: Optional[str] = None
    azure_sql_database: Optional[str] = None
    azure_sql_username: Optional[str] = None
    azure_sql_password: Optional[str] = None
    azure_sql_driver: str = "ODBC Driver 18 for SQL Server"
    use_sqlite_fallback: bool = True
    sqlite_path: str = "./data/dach_idp_dev.db"

    # ── Azure AD ──────────────────────────────────────────────
    use_managed_identity: bool = False
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None

    # ── GDPR ─────────────────────────────────────────────────
    gdpr_data_controller_name: str = "DACH IDP Demo GmbH"
    gdpr_data_controller_email: str = "datenschutz@dach-idp-demo.com"
    gdpr_data_controller_country: str = "DE"
    gdpr_audit_retention_years: int = 10
    gdpr_pii_masking_enabled: bool = True
    pii_encryption_key: Optional[str] = None

    # ── Confidence Thresholds ─────────────────────────────────
    invoice_confidence_threshold: float = 0.80
    cv_confidence_threshold: float = 0.75
    low_confidence_flag_threshold: float = 0.60

    # ── Languages ─────────────────────────────────────────────
    default_language: str = "de"
    supported_languages_raw: str = "de,en,fr,it"

    @property
    def supported_languages(self) -> List[str]:
        return [lang.strip() for lang in self.supported_languages_raw.split(",")]

    # ── Power BI ──────────────────────────────────────────────
    powerbi_workspace_id: Optional[str] = None
    powerbi_dataset_id: Optional[str] = None
    powerbi_client_id: Optional[str] = None
    powerbi_client_secret: Optional[str] = None
    powerbi_tenant_id: Optional[str] = None

    # ── Computed properties ───────────────────────────────────
    @property
    def is_mock_mode(self) -> bool:
        return self.app_mode == AppMode.MOCK

    @property
    def is_production(self) -> bool:
        return self.app_env == AppEnv.PRODUCTION

    @property
    def database_url(self) -> str:
        """Return the appropriate database URL."""
        if self.use_sqlite_fallback or self.app_mode == AppMode.MOCK:
            os.makedirs(os.path.dirname(self.sqlite_path) or ".", exist_ok=True)
            return f"sqlite+aiosqlite:///{self.sqlite_path}"
        if self.azure_sql_server and self.azure_sql_database:
            return (
                f"mssql+pyodbc://{self.azure_sql_username}:{self.azure_sql_password}"
                f"@{self.azure_sql_server}/{self.azure_sql_database}"
                f"?driver={self.azure_sql_driver.replace(' ', '+')}"
                f"&Encrypt=yes&TrustServerCertificate=no"
            )
        raise ValueError("No valid database configuration found.")

    @model_validator(mode="after")
    def validate_live_mode_requirements(self) -> "Settings":
        if self.app_mode == AppMode.LIVE:
            missing = []
            if not self.azure_doc_intel_endpoint:
                missing.append("AZURE_DOC_INTEL_ENDPOINT")
            if not self.azure_doc_intel_key:
                missing.append("AZURE_DOC_INTEL_KEY")
            if not self.azure_storage_connection_string:
                missing.append("AZURE_STORAGE_CONNECTION_STRING")
            if missing:
                raise ValueError(
                    f"LIVE mode requires these env vars: {', '.join(missing)}. "
                    "Set APP_MODE=mock to run without Azure credentials."
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
