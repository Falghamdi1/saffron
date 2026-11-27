"""Verification of Supabase access tokens, using a locally generated signing key."""

import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app.auth import TokenVerifier
from app.config import Settings
from app.main import create_app

ISSUER = "https://project.supabase.co/auth/v1"
USER_ID = "00000000-0000-0000-0000-0000000000aa"
KEY = ec.generate_private_key(ec.SECP256R1())


def supabase_settings(database_url="postgresql://localhost/unused"):
    return Settings(
        _env_file=None, auth_mode="supabase", database_url=database_url,
        supabase_url="https://project.supabase.co", supabase_anon_key="publishable",
        supabase_jwt_secret="",
    )


@pytest.fixture()
def verifier(monkeypatch):
    verifier = TokenVerifier(supabase_settings())
    public = SimpleNamespace(key=KEY.public_key())
    monkeypatch.setattr(verifier._jwks, "get_signing_key_from_jwt", lambda token: public)
    return verifier


def token(key=KEY, algorithm="ES256", **overrides):
    claims = {
        "sub": USER_ID, "role": "authenticated", "aud": "authenticated", "iss": ISSUER,
        "exp": int(time.time()) + 600, **overrides,
    }
    return jwt.encode(claims, key, algorithm=algorithm)


def test_valid_token_yields_the_subject(verifier):
    assert verifier.verify(token()).id == USER_ID


@pytest.mark.parametrize("overrides", [
    {"exp": 1}, {"aud": "anon"}, {"role": "anon"}, {"iss": "https://evil.example/auth/v1"},
    {"sub": "not-a-uuid"},
])
def test_invalid_claims_are_rejected(verifier, overrides):
    with pytest.raises((jwt.PyJWTError, ValueError)):
        verifier.verify(token(**overrides))


def test_token_signed_by_another_key_is_rejected(verifier):
    with pytest.raises(jwt.PyJWTError):
        verifier.verify(token(key=ec.generate_private_key(ec.SECP256R1())))


def test_symmetric_token_is_rejected_without_a_configured_secret(verifier):
    with pytest.raises(jwt.PyJWTError):
        verifier.verify(token(key="x" * 32, algorithm="HS256"))


def test_passwordless_sign_in_does_not_exist_in_production(database_url):
    with TestClient(create_app(supabase_settings(database_url))) as client:
        response = client.post("/api/local-auth/session", json={"name": "anyone"})
        assert response.status_code == 404
        assert client.get("/api/config").json()["auth_mode"] == "supabase"


def test_configuration_errors_never_echo_secrets():
    url = "postgresql://postgres.ref:[Sup3rSecret]@pooler.supabase.com:5432/postgres"
    with pytest.raises(ValueError, match="remove the") as error:
        supabase_settings(url)
    assert "Sup3rSecret" not in str(error.value)
