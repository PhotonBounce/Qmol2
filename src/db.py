from __future__ import annotations
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models import Base
import config

# Engine factory
if config.USE_POSTGRES:
    engine = create_async_engine(
        config.ASYNC_DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        echo=False,
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
else:
    engine = None
    AsyncSessionLocal = None


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async DB sessions."""
    if not config.USE_POSTGRES or AsyncSessionLocal is None:
        raise RuntimeError(
            "PostgreSQL is not configured. Set USE_POSTGRES=true in your environment."
        )
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables (for dev/testing only; use Alembic in production)."""
    if engine:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose the engine and clean up connections."""
    if engine:
        await engine.dispose()
