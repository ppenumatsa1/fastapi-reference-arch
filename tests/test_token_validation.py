import jwt
import pytest

from app.core.config import Settings
from app.core.exceptions import AuthenticationError
from app.core.security.auth import _allowed_audiences, validate_access_token


def _settings() -> Settings:
    return Settings(
        REQUIRE_AUTH=True,
        ENTRA_TENANT_ID="tenant-guid",
        ENTRA_API_AUDIENCE="api://41890f96-e753-4517-aebc-0043ce72c44c",
        ENTRA_AUTHORITY="https://login.microsoftonline.com",
    )


def _claims() -> dict[str, object]:
    return {
        "iss": "https://login.microsoftonline.com/tenant-guid/v2.0",
        "aud": "41890f96-e753-4517-aebc-0043ce72c44c",
        "appid": None,
        "azp": "a6e99561-168d-40bd-8059-73ba585b7737",
        "exp": 9999999999,
        "iat": 100,
        "tid": "tenant-guid",
        "sub": "subject",
        "jti": "token-id",
        "roles": ["Todos.Read"],
    }


def test_allowed_audiences_includes_guid_variant():
    settings = _settings()
    assert _allowed_audiences(settings) == [
        "api://41890f96-e753-4517-aebc-0043ce72c44c",
        "41890f96-e753-4517-aebc-0043ce72c44c",
    ]


def test_validate_access_token_accepts_azp_when_appid_missing(
    monkeypatch: pytest.MonkeyPatch,
):
    settings = _settings()

    monkeypatch.setattr(
        "app.core.security.auth._get_unverified_header",
        lambda _token: {"alg": "RS256", "kid": "kid-1"},
    )
    monkeypatch.setattr(
        "app.core.security.auth._jwks_cache.get_key",
        lambda *_args, **_kwargs: {"kty": "RSA", "n": "abc", "e": "AQAB"},
    )
    monkeypatch.setattr(
        jwt.algorithms.RSAAlgorithm,
        "from_jwk",
        lambda _jwk: "signing-key",
    )
    monkeypatch.setattr(
        "app.core.security.auth.jwt.decode",
        lambda *_a, **_k: _claims(),
    )

    context = validate_access_token("valid-token", settings)
    assert context.client_app_id == "a6e99561-168d-40bd-8059-73ba585b7737"


def test_validate_access_token_preserves_invalid_token_cause(
    monkeypatch: pytest.MonkeyPatch,
):
    settings = _settings()

    monkeypatch.setattr(
        "app.core.security.auth._get_unverified_header",
        lambda _token: {"alg": "RS256", "kid": "kid-1"},
    )
    monkeypatch.setattr(
        "app.core.security.auth._jwks_cache.get_key",
        lambda *_args, **_kwargs: {"kty": "RSA", "n": "abc", "e": "AQAB"},
    )
    monkeypatch.setattr(
        jwt.algorithms.RSAAlgorithm,
        "from_jwk",
        lambda _jwk: "signing-key",
    )

    root_cause = jwt.InvalidAudienceError("Audience doesn't match")
    monkeypatch.setattr(
        "app.core.security.auth.jwt.decode",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(root_cause),
    )

    with pytest.raises(AuthenticationError) as exc_info:
        validate_access_token("bad-audience-token", settings)

    assert exc_info.value.cause is root_cause
