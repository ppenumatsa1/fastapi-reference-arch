"""Token validation for Microsoft Entra access tokens."""

from __future__ import annotations

import json
import threading
import time
from urllib.request import Request, urlopen

import jwt

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.security.models import AuthContext

_ALLOWED_ALGORITHMS = ("RS256",)


class _JwksCache:
    """Simple in-memory JWKS cache with TTL and refresh-on-miss behavior."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._expires_at = 0.0
        self._keys_by_kid: dict[str, dict[str, object]] = {}

    def get_key(self, jwks_url: str, kid: str, ttl_seconds: int) -> dict[str, object]:
        with self._lock:
            keys = self._get_keys(jwks_url, ttl_seconds, force_refresh=False)
            if kid in keys:
                return keys[kid]

            keys = self._get_keys(jwks_url, ttl_seconds, force_refresh=True)
            if kid in keys:
                return keys[kid]

        raise AuthenticationError("Token signing key not found")

    def _get_keys(
        self,
        jwks_url: str,
        ttl_seconds: int,
        *,
        force_refresh: bool,
    ) -> dict[str, dict[str, object]]:
        now = time.time()
        if not force_refresh and self._keys_by_kid and now < self._expires_at:
            return self._keys_by_kid

        self._keys_by_kid = _fetch_jwks(jwks_url)
        self._expires_at = now + ttl_seconds
        return self._keys_by_kid


_jwks_cache = _JwksCache()


def validate_access_token(token: str, settings: Settings) -> AuthContext:
    """Validate a bearer access token and project claims into AuthContext."""

    _validate_auth_settings(settings)

    token_header = _get_unverified_header(token)
    algorithm = str(token_header.get("alg", ""))
    kid = str(token_header.get("kid", ""))
    if algorithm not in _ALLOWED_ALGORITHMS:
        raise AuthenticationError("Unsupported token algorithm")
    if not kid:
        raise AuthenticationError("Missing token signing key identifier")

    jwk = _jwks_cache.get_key(
        _build_jwks_url(settings),
        kid,
        settings.entra_jwks_cache_ttl_seconds,
    )
    signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))

    try:
        claims: dict[str, object] = jwt.decode(
            token,
            signing_key,
            algorithms=list(_ALLOWED_ALGORITHMS),
            audience=_allowed_audiences(settings),
            options={
                "require": ["exp", "iat", "iss", "aud"],
                "verify_iss": False,
            },
            leeway=settings.entra_clock_skew_seconds,
        )
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Invalid access token", cause=exc) from exc

    issuer = str(claims.get("iss", ""))
    if issuer not in _allowed_issuers(settings):
        raise AuthenticationError("Invalid token issuer")

    client_app_id = str(claims.get("appid") or claims.get("azp") or "").strip()
    if not client_app_id:
        raise AuthenticationError("Token missing app identity")

    roles = _normalize_roles(claims.get("roles"))
    return AuthContext(
        is_authenticated=True,
        tenant_id=str(claims.get("tid", "")).strip() or None,
        client_app_id=client_app_id,
        token_subject=str(claims.get("sub", "")).strip() or None,
        token_id=str(claims.get("jti", "")).strip() or None,
        roles=roles,
    )


def _validate_auth_settings(settings: Settings) -> None:
    if not settings.entra_tenant_id:
        raise AuthenticationError(
            "Authentication is enabled but tenant is not configured"
        )
    if not settings.entra_api_audience:
        raise AuthenticationError(
            "Authentication is enabled but API audience is not configured"
        )


def _build_jwks_url(settings: Settings) -> str:
    authority = settings.entra_authority.rstrip("/")
    tenant_id = settings.entra_tenant_id
    return f"{authority}/{tenant_id}/discovery/v2.0/keys"


def _allowed_issuers(settings: Settings) -> set[str]:
    authority = settings.entra_authority.rstrip("/")
    tenant_id = settings.entra_tenant_id
    return {
        f"{authority}/{tenant_id}/v2.0",
        f"https://sts.windows.net/{tenant_id}/",
    }


def _allowed_audiences(settings: Settings) -> list[str]:
    audience = settings.entra_api_audience
    if not audience:
        return []

    audiences = [audience]
    if audience.startswith("api://"):
        audiences.append(audience.removeprefix("api://"))

    return audiences


def _normalize_roles(raw_roles: object) -> list[str]:
    if isinstance(raw_roles, list):
        return [str(role) for role in raw_roles if str(role).strip()]
    return []


def _get_unverified_header(token: str) -> dict[str, object]:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise AuthenticationError("Malformed access token") from exc

    if not isinstance(header, dict):
        raise AuthenticationError("Malformed access token header")
    return header


def _fetch_jwks(jwks_url: str) -> dict[str, dict[str, object]]:
    request = Request(jwks_url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise AuthenticationError("Failed to fetch token signing keys") from exc

    keys = payload.get("keys") if isinstance(payload, dict) else None
    if not isinstance(keys, list):
        raise AuthenticationError("Invalid token signing keys payload")

    indexed: dict[str, dict[str, object]] = {}
    for key in keys:
        if not isinstance(key, dict):
            continue
        kid = key.get("kid")
        if isinstance(kid, str) and kid:
            indexed[kid] = key

    if not indexed:
        raise AuthenticationError("No signing keys available")

    return indexed
