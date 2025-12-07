"""Database session and engine helpers."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


settings = get_settings()
async_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.database_echo,
    future=True,
)
async_session_factory = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Provide a scoped async session for FastAPI dependencies."""
    async with async_session_factory() as session:
        yield session
