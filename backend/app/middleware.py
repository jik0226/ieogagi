"""ASGI middleware: CSRF origin check, security headers, session cookie refresh, request logging."""

from __future__ import annotations

import logging
import secrets
import time
from collections.abc import Mapping
from types import MappingProxyType

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.auth.cookies import SESSION_REFRESH_STATE, set_session_cookie
from app.config import Settings
from app.errors import Forbidden, PayloadTooLarge

logger = logging.getLogger("ieogagi.request")

UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
SECURITY_HEADERS: Mapping[str, str] = MappingProxyType(
    {
        "content-security-policy": "default-src 'none'; frame-ancestors 'none'",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "no-referrer",
        "cache-control": "no-store",
        "cross-origin-opener-policy": "same-origin",
        "cross-origin-resource-policy": "same-origin",
        "permissions-policy": "camera=(), microphone=(), geolocation=()",
    }
)
DOCS_PREFIX = "/api/docs"
MAX_BODY_BYTES = 64 * 1024  # largest legitimate body (a 2000-char note) is far below this


class OriginCheckMiddleware:
    """Reject state-changing requests whose Origin is missing or not allow-listed.

    Combined with SameSite=Strict cookies this blocks cross-site request
    forgery without needing CSRF tokens in the SPA.
    """

    def __init__(self, app: ASGIApp, allowed_origins: frozenset[str]) -> None:
        self.app = app
        self.allowed_origins = allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] in UNSAFE_METHODS:
            origin = Headers(scope=scope).get("origin")
            if origin is None or origin not in self.allowed_origins:
                logger.warning("csrf_origin_rejected", extra={"event": "csrf_origin_rejected"})
                error = Forbidden()
                response = JSONResponse(error.to_body(), status_code=error.status_code)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


class BodySizeLimitMiddleware:
    """Refuse oversized request bodies before they are parsed.

    A declared Content-Length above the limit is rejected immediately (413).
    Bodies without a length are counted while streaming; going over the limit
    aborts parsing with an error instead of buffering unbounded data.
    """

    def __init__(self, app: ASGIApp, max_bytes: int = MAX_BODY_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        declared = Headers(scope=scope).get("content-length")
        if declared is not None and (not declared.isdigit() or int(declared) > self.max_bytes):
            error = PayloadTooLarge()
            response = JSONResponse(error.to_body(), status_code=error.status_code)
            await response(scope, receive, send)
            return
        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    raise PayloadTooLarge
            return message

        await self.app(scope, limited_receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        is_docs = scope["path"].startswith(DOCS_PREFIX)

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS.items():
                    if is_docs and name == "content-security-policy":
                        continue  # dev-only Swagger UI needs its own scripts
                    headers[name] = value
            await send(message)

        await self.app(scope, receive, send_with_headers)


class SessionCookieRefreshMiddleware:
    """Re-issue the session cookie on authenticated responses (sliding Max-Age).

    ``get_current_user`` marks the request only after the session passed the server-side
    idle and absolute checks. The cookie is then sent again with Max-Age = idle timeout, so
    the browser copy expires no later than the server session. Responses that set the
    session cookie themselves (login, logout) are left untouched. Done here rather than in
    the dependency so endpoints that return a Response object directly are covered too.
    """

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        self.app = app
        self.settings = settings
        self.cookie_prefix = f"{settings.cookie_name}="

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_cookie(message: Message) -> None:
            if message["type"] == "http.response.start" and scope.get("state", {}).get(
                SESSION_REFRESH_STATE
            ):
                headers = MutableHeaders(scope=message)
                already_set = any(
                    value.startswith(self.cookie_prefix) for value in headers.getlist("set-cookie")
                )
                token = Request(scope).cookies.get(self.settings.cookie_name)
                if token and not already_set:
                    scratch = Response()
                    set_session_cookie(scratch, self.settings, token)
                    headers.append("set-cookie", scratch.headers["set-cookie"])
            await send(message)

        await self.app(scope, receive, send_with_cookie)


class RequestLogMiddleware:
    """One JSON log line per request: method, route template, status, duration.

    The raw path and query string are not logged (they may contain ids or
    filters); the matched route template is logged instead.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = secrets.token_hex(8)
        started = time.perf_counter()
        status_holder = {"status": 500}

        async def send_capturing(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                MutableHeaders(scope=message)["x-request-id"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_capturing)
        finally:
            route = scope.get("route")
            logger.info(
                "request",
                extra={
                    "event": "request",
                    "request_id": request_id,
                    "method": scope["method"],
                    "route": getattr(route, "path", "unmatched"),
                    "status": status_holder["status"],
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "user_id": scope.get("state", {}).get("user_id"),
                },
            )
