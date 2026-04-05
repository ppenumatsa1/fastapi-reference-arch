"""Security models used by authentication dependencies."""

from pydantic import BaseModel, Field


class AuthContext(BaseModel):
    """Represents authenticated application context extracted from access token."""

    is_authenticated: bool = False
    tenant_id: str | None = None
    client_app_id: str | None = None
    token_subject: str | None = None
    token_id: str | None = None
    roles: list[str] = Field(default_factory=list)


def anonymous_auth_context() -> AuthContext:
    """Return a fresh anonymous auth context for unauthenticated flows."""

    return AuthContext()
