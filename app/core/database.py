"""Database session and engine helpers."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import DbAuthMode, get_settings

try:
    from azure.identity.aio import DefaultAzureCredential
except ImportError:
    DefaultAzureCredential = None  # type: ignore


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


# Azure AD scope for PostgreSQL
POSTGRES_AAD_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"


async def get_aad_token() -> str:
    """Fetch Azure AD access token for PostgreSQL."""
    if DefaultAzureCredential is None:
        raise RuntimeError(
            "azure-identity package is required for AAD authentication. "
            "Install it with: pip install azure-identity"
        )

    credential = DefaultAzureCredential()
    token = await credential.get_token(POSTGRES_AAD_SCOPE)
    return token.token


def _create_engine_with_aad():
    """Create async engine with AAD token authentication."""
    settings = get_settings()

    async def get_connection_with_token():
        """Get connection with fresh AAD token."""
        import asyncpg

        token = await get_aad_token()

        # Parse database URL to get connection parameters
        # Format: postgresql+asyncpg://user@host:port/database?ssl=require
        url = settings.async_database_url
        if url.startswith("postgresql+asyncpg://"):
            url = url[21:]  # Remove postgresql+asyncpg://

        # Split user@host:port/database?params
        parts = url.split("@")
        user = parts[0]
        rest = parts[1]

        host_port_db = rest.split("?")[0]
        host_port, database = host_port_db.rsplit("/", 1)

        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
            port = int(port)
        else:
            host = host_port
            port = 5432

        # Create connection with token as password
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=token,
            database=database,
            ssl="require",
            server_settings={"application_name": settings.app_name},
        )
        return conn

    # Create engine with custom connection factory
    engine = create_async_engine(
        settings.async_database_url,
        echo=settings.database_echo,
        future=True,
        async_creator=get_connection_with_token,
    )

    return engine


def _create_engine_with_password():
    """Create async engine with password authentication."""
    settings = get_settings()
    return create_async_engine(
        settings.async_database_url,
        echo=settings.database_echo,
        future=True,
    )


settings = get_settings()

# Create engine based on auth mode
if settings.db_auth_mode == DbAuthMode.AAD:
    async_engine = _create_engine_with_aad()
else:
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
