"""
app/main.py
============
FastAPI application entry point for DACH IDP Platform.

Endpoints summary:
  POST /api/v1/invoices/upload   — Invoice upload + extraction
  GET  /api/v1/invoices/         — List invoices
  GET  /api/v1/invoices/{id}     — Get invoice result
  POST /api/v1/cvs/upload        — CV upload + extraction
  GET  /api/v1/cvs/              — List CVs
  GET  /api/v1/cvs/{id}          — Get CV result
  POST /api/v1/gdpr/dsr          — Submit data subject request
  GET  /api/v1/gdpr/health       — GDPR compliance health
  GET  /health                   — System health check
  GET  /                         — API info
  GET  /docs                     — Swagger UI
  GET  /redoc                    — ReDoc UI
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import ats, cvs, gdpr, invoices
from app.config import get_settings
from app.database.connection import create_tables

log = structlog.get_logger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ──────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    log.info(
        "startup",
        mode=settings.app_mode.value,
        env=settings.app_env.value,
        version=settings.app_version,
    )

    # Create DB tables (SQLite in mock/dev, Azure SQL in prod)
    try:
        await create_tables()
        log.info("database_tables_created")
    except Exception as e:
        log.warning("database_init_failed", error=str(e))

    # Ensure mock storage directory exists
    if settings.is_mock_mode:
        import os
        os.makedirs("./data/mock_storage", exist_ok=True)
        log.info("mock_storage_ready")

    yield

    log.info("shutdown")


# ──────────────────────────────────────────────────────────────────────────────
# App creation
# ──────────────────────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="DACH Intelligent Document Processing Platform",
        description=(
            "End-to-end PDF processing for invoices and CVs/resumes. "
            "Focused on Germany (DE), Switzerland (CH), and Austria (AT). "
            "Azure AI Engineer / AI-102 aligned. GDPR / DSGVO compliant.\n\n"
            "**Modes**: Set `APP_MODE=mock` for demo without Azure credentials, "
            "or `APP_MODE=live` for full Azure AI Document Intelligence extraction.\n\n"
            "**Languages**: German (DE), English (EN), French (FR), Italian (IT)\n\n"
            "**Currencies**: EUR (DE/AT), CHF (CH)\n\n"
            "**GDPR**: Consent tracking, audit logs, DSR handling, PII masking, "
            "retention management (HGB §257, AO §147, OR Art. 958f)."
        ),
        version=settings.app_version,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=[
            {"name": "Invoices", "description": "Invoice upload, extraction, and review workflows."},
            {"name": "CVs / Resumes", "description": "CV extraction, ATS scoring, recruiter intelligence."},
            {"name": "GDPR / DSGVO Compliance", "description": "Consent, DSR, audit logs, PII masking, retention."},
        ],
    )

    # ── Middleware ───────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if not settings.is_production else ["https://your-domain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["your-domain.com", "*.azurewebsites.net"],
        )

    # ── Request timing middleware ────────────────────────────────────────────
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        response.headers["X-Process-Time"] = f"{duration:.4f}"
        return response

    # ── Global exception handler ─────────────────────────────────────────────
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        log.error("unhandled_exception", error=str(exc), path=request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc) if not settings.is_production else "An unexpected error occurred.",
            },
        )

    # ── Static files (dashboard) ─────────────────────────────────────────────
    import os
    dashboard_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dashboard")
    if os.path.isdir(dashboard_path):
        app.mount("/dashboard", StaticFiles(directory=dashboard_path, html=True), name="dashboard")

    # ── Routers ──────────────────────────────────────────────────────────────
    app.include_router(invoices.router)
    app.include_router(cvs.router)
    app.include_router(gdpr.router)
    app.include_router(ats.router)

    # ── Root endpoints ───────────────────────────────────────────────────────
    @app.get("/", tags=["System"], summary="API information")
    async def root():
        return {
            "name": "DACH Intelligent Document Processing Platform",
            "version": settings.app_version,
            "mode": settings.app_mode.value,
            "environment": settings.app_env.value,
            "documentation": "/docs",
            "languages": settings.supported_languages,
            "gdpr_controller": settings.gdpr_data_controller_name,
            "endpoints": {
                "invoices": "/api/v1/invoices",
                "cvs": "/api/v1/cvs",
                "gdpr": "/api/v1/gdpr",
                "ats": "/api/v1/ats",
                "health": "/health",
            },
        }

    @app.get("/health", tags=["System"], summary="Health check")
    async def health():
        return {
            "status": "ok",
            "mode": settings.app_mode.value,
            "version": settings.app_version,
            "azure_doc_intel": "configured" if settings.azure_doc_intel_endpoint else "not_configured (mock mode)",
            "azure_blob": "configured" if settings.azure_storage_connection_string else "not_configured (local)",
        }

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_env.value == "development",
        log_level=settings.log_level.lower(),
    )
