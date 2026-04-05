import pytest
from httpx import AsyncClient

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.core.security.models import AuthContext
from app.main import app

API_PREFIX = "/api/v1"


def _auth_enabled_settings() -> Settings:
    return Settings(
        REQUIRE_AUTH=True,
        ENTRA_TENANT_ID="test-tenant-id",
        ENTRA_API_AUDIENCE="api://test-api",
    )


def _valid_auth_context(*, roles: list[str]) -> AuthContext:
    return AuthContext(
        is_authenticated=True,
        tenant_id="test-tenant-id",
        client_app_id="test-client-id",
        token_subject="subject",
        token_id="token-id",
        roles=roles,
    )


@pytest.mark.asyncio
async def test_health_endpoint_is_public_when_auth_enabled(client: AsyncClient):
    app.dependency_overrides[get_settings] = _auth_enabled_settings
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_missing_bearer_token_returns_401(client: AsyncClient):
    app.dependency_overrides[get_settings] = _auth_enabled_settings
    response = await client.get(f"{API_PREFIX}/todos/?limit=1&offset=0")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


@pytest.mark.asyncio
async def test_invalid_bearer_token_returns_401(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    app.dependency_overrides[get_settings] = _auth_enabled_settings

    def mock_validate_access_token(token: str, settings: Settings) -> AuthContext:
        raise AuthenticationError("Invalid access token")

    monkeypatch.setattr(
        "app.core.security.dependencies.validate_access_token",
        mock_validate_access_token,
    )

    response = await client.get(
        f"{API_PREFIX}/todos/?limit=1&offset=0",
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


@pytest.mark.asyncio
async def test_missing_required_role_returns_403(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    app.dependency_overrides[get_settings] = _auth_enabled_settings

    def mock_validate_access_token(token: str, settings: Settings) -> AuthContext:
        return _valid_auth_context(roles=[])

    monkeypatch.setattr(
        "app.core.security.dependencies.validate_access_token",
        mock_validate_access_token,
    )

    response = await client.get(
        f"{API_PREFIX}/todos/?limit=1&offset=0",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "authorization_error"


@pytest.mark.asyncio
async def test_valid_role_allows_access(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    app.dependency_overrides[get_settings] = _auth_enabled_settings

    def mock_validate_access_token(token: str, settings: Settings) -> AuthContext:
        return _valid_auth_context(roles=["Todos.Read"])

    monkeypatch.setattr(
        "app.core.security.dependencies.validate_access_token",
        mock_validate_access_token,
    )

    response = await client.get(
        f"{API_PREFIX}/todos/?limit=1&offset=0",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_read_role_cannot_create_todo(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    app.dependency_overrides[get_settings] = _auth_enabled_settings

    def mock_validate_access_token(token: str, settings: Settings) -> AuthContext:
        return _valid_auth_context(roles=["Todos.Read"])

    monkeypatch.setattr(
        "app.core.security.dependencies.validate_access_token",
        mock_validate_access_token,
    )

    response = await client.post(
        f"{API_PREFIX}/todos/",
        headers={"Authorization": "Bearer valid-token"},
        json={"title": "should fail"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "authorization_error"


@pytest.mark.asyncio
async def test_write_role_can_read_and_create(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
):
    app.dependency_overrides[get_settings] = _auth_enabled_settings

    def mock_validate_access_token(token: str, settings: Settings) -> AuthContext:
        return _valid_auth_context(roles=["Todos.Write"])

    monkeypatch.setattr(
        "app.core.security.dependencies.validate_access_token",
        mock_validate_access_token,
    )

    read_response = await client.get(
        f"{API_PREFIX}/todos/?limit=1&offset=0",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert read_response.status_code == 200

    create_response = await client.post(
        f"{API_PREFIX}/todos/",
        headers={"Authorization": "Bearer valid-token"},
        json={"title": "created with write"},
    )
    assert create_response.status_code == 201
