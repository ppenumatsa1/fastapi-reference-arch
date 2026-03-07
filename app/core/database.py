"""Database session and engine helpers."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def _create_engine_with_password():
    """Create async engine with password authentication."""
    settings = get_settings()

    engine_kwargs: dict[str, object] = {
        "echo": settings.database_echo,
        "future": True,
    }

    # SQLite pool options differ; keep defaults for sqlite-based tests/dev usage.
    if not settings.async_database_url.startswith("sqlite"):
        engine_kwargs.update(
            {
                "pool_size": settings.database_pool_size,
                "max_overflow": settings.database_max_overflow,
                "pool_timeout": settings.database_pool_timeout,
                "pool_recycle": settings.database_pool_recycle,
                "pool_pre_ping": settings.database_pool_pre_ping,
            }
        )

    return create_async_engine(
        settings.async_database_url,
        **engine_kwargs,
    )


settings = get_settings()

async_engine = _create_engine_with_password()

async_session_factory = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Provide a scoped async session for FastAPI dependencies."""
    async with async_session_factory() as session:
        yield session
