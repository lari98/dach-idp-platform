"""
app/database/connection.py
============================
Async database engine / session factory.
Supports: Azure SQL (pyodbc / MSSQL) and SQLite (local dev / mock).
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.database.models import Base

settings = get_settings()

# Create engine once at module level
engine = create_async_engine(
    settings.database_url,
    echo=(settings.log_level == "DEBUG"),
    pool_pre_ping=True,
    # For SQLite in-memory/file: disable pool
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def create_tables() -> None:
    """Create all tables. Called at startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
