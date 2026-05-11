"""
app/services/blob_storage.py
==============================
Azure Blob Storage service for uploading/downloading documents.
Falls back to local filesystem in mock mode.

Security:
  - Generates SAS URLs with short TTL for secure access
  - Files stored with server-side encryption (SSE)
  - Container-level access policy: private
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Tuple

import aiofiles
import structlog

from app.config import AppMode, get_settings

log = structlog.get_logger(__name__)
settings = get_settings()

# Local mock storage path
MOCK_STORAGE_PATH = Path("./data/mock_storage")


class BlobStorageService:
    """
    Abstracts Azure Blob Storage. In mock mode, stores to local filesystem.
    """

    def __init__(self):
        self.settings = settings
        self._blob_service_client = None

    def _get_blob_service_client(self):
        """Lazy-load Azure SDK client."""
        if self._blob_service_client is None:
            from azure.storage.blob import BlobServiceClient
            self._blob_service_client = BlobServiceClient.from_connection_string(
                self.settings.azure_storage_connection_string
            )
        return self._blob_service_client

    async def upload_document(
        self,
        file_bytes: bytes,
        original_filename: str,
        document_type: str,   # "invoice" | "cv"
        document_id: Optional[str] = None,
    ) -> Tuple[str, str]:
        """
        Upload a document to storage.

        Returns:
            Tuple of (document_id, blob_url_or_path)
        """
        if not document_id:
            document_id = str(uuid.uuid4())

        safe_filename = self._sanitise_filename(original_filename)
        blob_name = f"{document_id}/{safe_filename}"

        if self.settings.is_mock_mode:
            return await self._upload_mock(file_bytes, blob_name, document_type, document_id)

        return await self._upload_azure(file_bytes, blob_name, document_type, document_id)

    async def _upload_azure(
        self,
        file_bytes: bytes,
        blob_name: str,
        document_type: str,
        document_id: str,
    ) -> Tuple[str, str]:
        """Upload to Azure Blob Storage."""
        container = (
            self.settings.azure_storage_container_invoices
            if document_type == "invoice"
            else self.settings.azure_storage_container_cvs
        )

        client = self._get_blob_service_client()
        blob_client = client.get_blob_client(container=container, blob=blob_name)

        blob_client.upload_blob(
            file_bytes,
            overwrite=True,
            metadata={
                "document_id": document_id,
                "document_type": document_type,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        blob_url = blob_client.url
        log.info("azure_blob_uploaded", blob_name=blob_name, container=container)
        return document_id, blob_url

    async def _upload_mock(
        self,
        file_bytes: bytes,
        blob_name: str,
        document_type: str,
        document_id: str,
    ) -> Tuple[str, str]:
        """Save to local filesystem for mock mode."""
        storage_dir = MOCK_STORAGE_PATH / document_type / document_id
        storage_dir.mkdir(parents=True, exist_ok=True)

        filename = Path(blob_name).name
        file_path = storage_dir / filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_bytes)

        mock_url = f"mock://storage/{document_type}/{document_id}/{filename}"
        log.info("mock_storage_saved", path=str(file_path))
        return document_id, mock_url

    async def generate_sas_url(
        self,
        blob_url: str,
        expiry_hours: int = 1,
    ) -> str:
        """
        Generate a time-limited SAS URL for secure document access.
        In mock mode, returns the local path.
        """
        if self.settings.is_mock_mode or blob_url.startswith("mock://"):
            return blob_url

        from azure.storage.blob import (
            BlobSasPermissions,
            BlobServiceClient,
            generate_blob_sas,
        )
        from urllib.parse import urlparse

        parsed = urlparse(blob_url)
        path_parts = parsed.path.lstrip("/").split("/", 1)
        container_name = path_parts[0]
        blob_name = path_parts[1] if len(path_parts) > 1 else ""

        client = self._get_blob_service_client()
        account_key = client.credential.account_key

        sas_token = generate_blob_sas(
            account_name=self.settings.azure_storage_account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(hours=expiry_hours),
        )

        return f"{blob_url}?{sas_token}"

    async def delete_blob(self, blob_url: str) -> bool:
        """
        Delete a blob. Used for GDPR Art. 17 erasure requests.
        Returns True if deleted, False if not found.
        """
        if self.settings.is_mock_mode or blob_url.startswith("mock://"):
            # Parse mock path
            mock_path = blob_url.replace("mock://storage/", str(MOCK_STORAGE_PATH) + "/")
            if os.path.exists(mock_path):
                os.remove(mock_path)
                log.info("mock_blob_deleted", path=mock_path)
                return True
            return False

        from azure.storage.blob import BlobServiceClient
        from urllib.parse import urlparse

        parsed = urlparse(blob_url)
        path_parts = parsed.path.lstrip("/").split("/", 1)
        container_name = path_parts[0]
        blob_name = path_parts[1] if len(path_parts) > 1 else ""

        client = self._get_blob_service_client()
        blob_client = client.get_blob_client(container=container_name, blob=blob_name)

        try:
            blob_client.delete_blob()
            log.info("azure_blob_deleted", blob_name=blob_name)
            return True
        except Exception as e:
            log.warning("azure_blob_delete_failed", error=str(e))
            return False

    async def list_blobs(self, document_type: str) -> list:
        """List blobs in a container (for admin/audit use)."""
        if self.settings.is_mock_mode:
            storage_dir = MOCK_STORAGE_PATH / document_type
            if not storage_dir.exists():
                return []
            return [str(p) for p in storage_dir.rglob("*.pdf")]

        container = (
            self.settings.azure_storage_container_invoices
            if document_type == "invoice"
            else self.settings.azure_storage_container_cvs
        )
        client = self._get_blob_service_client()
        container_client = client.get_container_client(container)
        return [b.name for b in container_client.list_blobs()]

    @staticmethod
    def _sanitise_filename(filename: str) -> str:
        """Sanitise filename to prevent path traversal."""
        safe = os.path.basename(filename)
        safe = "".join(c for c in safe if c.isalnum() or c in "._- ")
        return safe[:200] or "document.pdf"
