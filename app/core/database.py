"""Database session and engine helpers."""

import time
from collections.abc import AsyncIterator
from threading import Lock

from sqlalchemy import event
from sqlalchemy import exc as sa_exc
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

POSTGRES_ENTRA_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"
CONNECTION_EXPIRY_GUARD_SECONDS = 60


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


class _PostgresTokenProvider:
    """Caches Entra tokens for database login and refreshes before expiry."""

    def __init__(self):
        try:
            from azure.identity import DefaultAzureCredential, ManagedIdentityCredential
        except ImportError as exc:  # pragma: no cover - enforced in packaging
            raise RuntimeError(
                "azure-identity is required for Entra database authentication"
            ) from exc

        settings = get_settings()
        if settings.azure_client_id:
            self._credential = ManagedIdentityCredential(
                client_id=settings.azure_client_id
            )
        else:
            self._credential = DefaultAzureCredential(
                exclude_interactive_browser_credential=True
            )

        self._token: str | None = None
        self._expires_on: float = 0
        self._lock = Lock()
        self._refresh_skew_seconds = max(
            30, settings.entra_db_token_refresh_skew_seconds
        )

    def get_token(self) -> tuple[str, float]:
        now = time.time()
        with self._lock:
            if self._token and now < self._expires_on - self._refresh_skew_seconds:
                return self._token, self._expires_on

            token = self._credential.get_token(POSTGRES_ENTRA_SCOPE)
            self._token = token.token
            self._expires_on = float(token.expires_on)
            return self._token, self._expires_on


def _safe_entra_pool_recycle_seconds() -> int:
    """Clamp pool recycle so pooled connections retire before token expiry."""
    settings = get_settings()
    token_lifetime = max(120, settings.entra_db_token_lifetime_seconds)
    refresh_skew = max(30, settings.entra_db_token_refresh_skew_seconds)
    recycle_ceiling = max(60, token_lifetime - refresh_skew)
    return min(settings.database_pool_recycle, recycle_ceiling)


def _create_engine_with_entra():
    """Create async engine that injects Entra access token for each new connection."""
    settings = get_settings()

    engine_kwargs: dict[str, object] = {
        "echo": settings.database_echo,
        "future": True,
    }

    engine_kwargs.update(
        {
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_timeout": settings.database_pool_timeout,
            "pool_recycle": _safe_entra_pool_recycle_seconds(),
            "pool_pre_ping": settings.database_pool_pre_ping,
        }
    )

    engine = create_async_engine(
        settings.async_database_url,
        **engine_kwargs,
    )

    token_provider = _PostgresTokenProvider()

    @event.listens_for(engine.sync_engine, "do_connect")
    def _inject_access_token(dialect, conn_rec, cargs, cparams):  # noqa: ARG001
        token, expires_on = token_provider.get_token()
        cparams["password"] = token
        conn_rec.info["entra_token_expires_on"] = expires_on

    @event.listens_for(engine.sync_engine, "checkout")
    def _invalidate_near_expiry_connections(
        dbapi_conn, conn_rec, conn_proxy
    ):  # noqa: ARG001
        expires_on = float(conn_rec.info.get("entra_token_expires_on", 0))
        now = time.time()
        if now >= expires_on - CONNECTION_EXPIRY_GUARD_SECONDS:
            conn_rec.invalidate()
            raise sa_exc.DisconnectionError(
                "Discarding pooled connection with near-expiry Entra token"
            )

    return engine


settings = get_settings()

if settings.use_entra_db_auth and not settings.async_database_url.startswith("sqlite"):
    async_engine = _create_engine_with_entra()
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
