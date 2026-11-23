"""FastAPI application factory.

Run with: ``uvicorn app.main:create_app --factory --proxy-headers
--forwarded-allow-ips <proxy-ip> --no-access-log``.
"""

from __future__ import annotations

from fastapi import FastAPI

from app.clock import Clock
from app.config import AppSecrets, Settings, get_settings, load_secrets
from app.db import build_engine, build_session_factory
from app.error_handlers import register_error_handlers
from app.logging_setup import configure_logging
from app.middleware import (
    BodySizeLimitMiddleware,
    OriginCheckMiddleware,
    RequestLogMiddleware,
    SecurityHeadersMiddleware,
    SessionCookieRefreshMiddleware,
)
from app.routers import accounts, auth, children, health, notes, records
from app.security.ratelimit import limiter

API_VERSION = "0.1.0"


def create_app(
    settings: Settings | None = None,
    secrets: AppSecrets | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    secrets = secrets or load_secrets(settings)
    configure_logging(settings.log_level, include_traceback=not settings.is_production)

    docs_enabled = not settings.is_production
    app = FastAPI(
        title="이어가기 API",
        version=API_VERSION,
        debug=False,
        docs_url="/api/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if docs_enabled else None,
        swagger_ui_oauth2_redirect_url=None,
    )
    engine = build_engine(secrets.database_url)
    app.state.settings = settings
    app.state.secrets = secrets
    app.state.engine = engine
    app.state.session_factory = build_session_factory(engine)
    app.state.clock = clock or Clock()
    limiter.enabled = settings.rate_limit_enabled
    app.state.limiter = limiter

    register_error_handlers(app)
    # Starlette runs the last-added middleware first: logging wraps everything,
    # then headers, the CSRF origin check, the body size limit, and the session cookie
    # refresh right before routing (it only adds Set-Cookie to authenticated responses).
    app.add_middleware(SessionCookieRefreshMiddleware, settings=settings)
    app.add_middleware(BodySizeLimitMiddleware)
    app.add_middleware(OriginCheckMiddleware, allowed_origins=frozenset(settings.allowed_origins))
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLogMiddleware)

    for module in (health, auth, accounts, children, records, notes):
        app.include_router(module.router)
    return app
