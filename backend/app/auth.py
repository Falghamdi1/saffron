"""Access token verification. The user id only ever comes from a verified token."""

import time
import uuid
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings

AUDIENCE = "authenticated"
LOCAL_ISSUER = "saffron-local"
bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class User:
    id: str
    email: str = ""


class TokenVerifier:
    def __init__(self, settings: Settings) -> None:
        if settings.auth_mode == "local":
            self._secret = settings.local_jwt_secret
            self._issuer = LOCAL_ISSUER
            self._jwks = None
        else:
            base = f"{settings.supabase_url.rstrip('/')}/auth/v1"
            self._secret = settings.supabase_jwt_secret
            self._issuer = base
            self._jwks = jwt.PyJWKClient(f"{base}/.well-known/jwks.json", cache_keys=True)

    def verify(self, token: str) -> User:
        algorithm = jwt.get_unverified_header(token).get("alg")
        # The key type is chosen by us, so a token cannot downgrade the algorithm.
        if algorithm == "HS256" and self._secret:
            key, algorithms = self._secret, ["HS256"]
        elif algorithm in ("ES256", "RS256") and self._jwks:
            key, algorithms = self._jwks.get_signing_key_from_jwt(token).key, [algorithm]
        else:
            raise jwt.InvalidTokenError("Unsupported signing algorithm")
        claims = jwt.decode(
            token, key, algorithms=algorithms, audience=AUDIENCE, issuer=self._issuer,
            options={"require": ["exp", "sub", "aud", "iss"]},
        )
        if claims.get("role") != AUDIENCE:
            raise jwt.InvalidTokenError("Not a signed-in user token")
        return User(id=str(uuid.UUID(claims["sub"])), email=claims.get("email", ""))


def issue_local_token(settings: Settings, user_id: str, email: str) -> str:
    now = int(time.time())
    claims = {
        "sub": user_id, "email": email, "role": AUDIENCE, "aud": AUDIENCE,
        "iss": LOCAL_ISSUER, "iat": now, "exp": now + 12 * 3600,
    }
    return jwt.encode(claims, settings.local_jwt_secret, algorithm="HS256")


def current_user(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)
) -> User:
    if credentials is None:
        raise HTTPException(401, "Sign in required")
    try:
        return request.app.state.verifier.verify(credentials.credentials)
    except (jwt.PyJWTError, ValueError) as error:
        raise HTTPException(401, "Your session is invalid or has expired") from error
