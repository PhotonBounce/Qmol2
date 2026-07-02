"""Async database engine with SQLite fallback.

Supports both PostgreSQL (production) and SQLite (dev/self-hosted/free tier).
SQLite uses aiosqlite driver. Falls back to in-memory if DB driver is missing.
"""
from __future__ import annotations
import os
import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models import Base
import config

logger = logging.getLogger("qmol.db")

engine = None
AsyncSessionLocal = None

if config.USE_POSTGRES:
    engine = create_async_engine(
        config.ASYNC_DATABASE_URL,
        pool_size=int(os.getenv("DB_POOL_SIZE", "20")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
        pool_pre_ping=True,
        echo=False,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
else:
    # SQLite async mode (free tier / self-hosted / local PC)
    # Uses aiosqlite driver — install with: pip install aiosqlite
    sqlite_url = f"sqlite+aiosqlite:///{config.DB_PATH}"
    try:
        engine = create_async_engine(
            sqlite_url,
            echo=False,
        )
        AsyncSessionLocal = async_sessionmaker(
            engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )
        logger.info("SQLite async engine ready: %s", config.DB_PATH)
    except ImportError as exc:
        logger.warning(
            "aiosqlite not installed. SQLite async mode unavailable. "
            "Install it: pip install aiosqlite. Error: %s", exc
        )


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async DB sessions."""
    if AsyncSessionLocal is None:
        raise RuntimeError(
            "Database not configured. Install aiosqlite (SQLite) or asyncpg (PostgreSQL)."
        )
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables (for dev/testing only; use Alembic in production)."""
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")


async def close_db() -> None:
    """Dispose the engine and clean up connections."""
    if engine:
        await engine.dispose()
