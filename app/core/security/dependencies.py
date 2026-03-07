"""FastAPI authentication and authorization dependencies."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security.auth import validate_access_token
from app.core.security.models import AuthContext, anonymous_auth_context

_bearer_scheme = HTTPBearer(auto_error=False)
_ROLE_IMPLICATIONS: dict[str, set[str]] = {
    "Todos.Write": {"Todos.Read"},
}


async def get_auth_context(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer_scheme),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthContext:
    """Build authenticated context from the bearer token when auth is enabled."""

    if not settings.require_auth:
        return anonymous_auth_context()

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Missing bearer token")

    auth_context = validate_access_token(credentials.credentials, settings)
    request.state.client_app_id = auth_context.client_app_id
    request.state.auth_roles = auth_context.roles
    return auth_context


def require_roles(*required_roles: str) -> Callable[..., AuthContext]:
    """Return a dependency that enforces required application roles."""

    expected_roles = tuple(role for role in required_roles if role)

    async def _enforce_roles(
        auth_context: Annotated[AuthContext, Depends(get_auth_context)],
    ) -> AuthContext:
        if not auth_context.is_authenticated:
            return auth_context

        effective_roles = _expand_effective_roles(auth_context.roles)
        missing_roles = [role for role in expected_roles if role not in effective_roles]
        if missing_roles:
            raise AuthorizationError(
                f"Missing required role(s): {', '.join(missing_roles)}"
            )

        return auth_context

    return _enforce_roles


def _expand_effective_roles(roles: list[str]) -> set[str]:
    effective = set(roles)
    for role in roles:
        effective.update(_ROLE_IMPLICATIONS.get(role, set()))
    return effective
