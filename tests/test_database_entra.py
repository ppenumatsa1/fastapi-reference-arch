import sys
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import exc as sa_exc

import app.core.database as database
from app.core.config import Settings


class _Token:
    def __init__(self, token: str, expires_on: float):
        self.token = token
        self.expires_on = expires_on


class _CredentialStub:
    def __init__(self, tokens: list[_Token]):
        self._tokens = tokens
        self.calls = 0

    def get_token(self, _scope: str) -> _Token:
        value = self._tokens[min(self.calls, len(self._tokens) - 1)]
        self.calls += 1
        return value


class _ConnRecStub:
    def __init__(self):
        self.info: dict[str, float] = {}
        self.invalidated = False

    def invalidate(self) -> None:
        self.invalidated = True


def _install_azure_identity_stub(
    monkeypatch: pytest.MonkeyPatch,
    credential: object,
) -> None:
    identity_module = SimpleNamespace(
        DefaultAzureCredential=lambda **kwargs: credential,
        ManagedIdentityCredential=lambda **kwargs: credential,
    )
    monkeypatch.setitem(sys.modules, "azure.identity", identity_module)


def test_postgres_token_provider_reuses_cached_token(monkeypatch: pytest.MonkeyPatch):
    now = time.time()
    credential = _CredentialStub(
        [
            _Token("token-1", now + 3600),
            _Token("token-2", now + 7200),
        ]
    )
    _install_azure_identity_stub(monkeypatch, credential)
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: Settings(
            DB_AUTH_MODE="aad",
            ENTRA_DB_TOKEN_REFRESH_SKEW_SECONDS=300,
        ),
    )

    provider = database._PostgresTokenProvider()
    token_1, _ = provider.get_token()
    token_2, _ = provider.get_token()

    assert token_1 == "token-1"
    assert token_2 == "token-1"
    assert credential.calls == 1


def test_postgres_token_provider_refreshes_near_expiry(monkeypatch: pytest.MonkeyPatch):
    now = time.time()
    credential = _CredentialStub(
        [
            _Token("token-1", now + 120),
            _Token("token-2", now + 3600),
        ]
    )
    _install_azure_identity_stub(monkeypatch, credential)
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: Settings(
            DB_AUTH_MODE="aad",
            ENTRA_DB_TOKEN_REFRESH_SKEW_SECONDS=300,
        ),
    )

    provider = database._PostgresTokenProvider()
    first, _ = provider.get_token()
    second, _ = provider.get_token()

    assert first == "token-1"
    assert second == "token-2"
    assert credential.calls == 2


def test_safe_entra_pool_recycle_is_clamped(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: Settings(
            DB_AUTH_MODE="aad",
            DATABASE_POOL_RECYCLE=7200,
            ENTRA_DB_TOKEN_LIFETIME_SECONDS=3600,
            ENTRA_DB_TOKEN_REFRESH_SKEW_SECONDS=300,
        ),
    )

    assert database._safe_entra_pool_recycle_seconds() == 3300


def test_engine_events_inject_token_and_invalidate_stale_checkout(
    monkeypatch: pytest.MonkeyPatch,
):
    callbacks: dict[str, object] = {}
    engine_kwargs: dict[str, object] = {}

    class _EngineStub:
        def __init__(self):
            self.sync_engine = object()

    engine = _EngineStub()

    class _ProviderStub:
        def get_token(self) -> tuple[str, float]:
            return "entra-token", time.time() + 900

    def fake_listens_for(_target: object, event_name: str):
        def decorator(fn):
            callbacks[event_name] = fn
            return fn

        return decorator

    def fake_create_async_engine(_url: str, **kwargs):
        engine_kwargs.update(kwargs)
        return engine

    monkeypatch.setattr(database.event, "listens_for", fake_listens_for)
    monkeypatch.setattr(database, "create_async_engine", fake_create_async_engine)
    monkeypatch.setattr(database, "_PostgresTokenProvider", _ProviderStub)
    monkeypatch.setattr(
        database,
        "get_settings",
        lambda: Settings(
            DB_AUTH_MODE="aad",
            DATABASE_HOST="db.contoso.local",
            DATABASE_NAME="postgres",
            DATABASE_USER="uami-principal",
            DATABASE_POOL_SIZE=5,
            DATABASE_MAX_OVERFLOW=5,
            DATABASE_POOL_TIMEOUT=20,
            DATABASE_POOL_RECYCLE=7200,
            ENTRA_DB_TOKEN_LIFETIME_SECONDS=3600,
            ENTRA_DB_TOKEN_REFRESH_SKEW_SECONDS=300,
        ),
    )

    created_engine = database._create_engine_with_entra()

    assert created_engine is engine
    assert engine_kwargs["pool_recycle"] == 3300
    assert "do_connect" in callbacks
    assert "checkout" in callbacks

    conn_rec = _ConnRecStub()
    cparams: dict[str, object] = {}
    callbacks["do_connect"](None, conn_rec, [], cparams)
    assert cparams["password"] == "entra-token"
    assert conn_rec.info["entra_token_expires_on"] > time.time()

    conn_rec.info["entra_token_expires_on"] = time.time() + 10
    with pytest.raises(sa_exc.DisconnectionError):
        callbacks["checkout"](None, conn_rec, None)
    assert conn_rec.invalidated is True
