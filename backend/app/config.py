"""Runtime configuration, read from environment variables or a local .env file."""

import secrets
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
LOOPBACK = ("localhost", "127.0.0.1")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    auth_mode: Literal["supabase", "local"] = "local"
    database_url: str = ""
    supabase_url: str = ""
    supabase_anon_key: str = ""
    # Only for Supabase projects that still sign tokens with the legacy HS256 secret.
    supabase_jwt_secret: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    local_jwt_secret: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    chat_rate_limit_per_minute: int = 20

    @model_validator(mode="after")
    def check_auth_mode(self) -> "Settings":
        if self.auth_mode == "supabase":
            missing = [
                name for name in ("database_url", "supabase_url", "supabase_anon_key")
                if not getattr(self, name)
            ]
            if missing:
                raise ValueError(f"Supabase mode requires: {', '.join(missing).upper()}")
        # Local sign-in has no passwords, so it must never front a remote database.
        elif self.database_url and urlparse(self.database_url).hostname not in LOOPBACK:
            raise ValueError("AUTH_MODE=local only works with a database on this machine")
        return self
