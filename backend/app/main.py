"""Application factory. Run with: uvicorn app.main:create_app --factory"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import router
from app.auth import TokenVerifier
from app.config import ROOT_DIR, Settings
from app.db import Database
from app.rate_limit import RateLimiter
from app.setup_db import setup_database
from app.understanding.llm import GeminiProvider, UnderstandingProvider

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
}


def _embedded_database() -> str:
    """Local mode without DATABASE_URL: run a private PostgreSQL in .localdb/."""
    import pgserver

    server = pgserver.get_server(ROOT_DIR / ".localdb", cleanup_mode="stop")
    url = server.get_uri()
    setup_database(url, local=True)
    return url


def create_app(
    settings: Settings | None = None, provider: UnderstandingProvider | None = None
) -> FastAPI:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("pgserver", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    settings = settings or Settings()
    if provider is None and settings.gemini_api_key:
        provider = GeminiProvider(settings.gemini_api_key, settings.gemini_model)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.database = Database(settings.database_url or _embedded_database())
        yield
        app.state.database.close()

    app = FastAPI(title="Saffron AI", lifespan=lifespan)
    app.state.settings = settings
    app.state.provider = provider
    app.state.verifier = TokenVerifier(settings)
    app.state.rate_limiter = RateLimiter(settings.chat_rate_limit_per_minute)

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    app.include_router(router)
    if FRONTEND_DIST.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
    return app
