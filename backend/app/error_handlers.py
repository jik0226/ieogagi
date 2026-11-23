"""Global exception handlers.

Clients only ever receive ``{"error": {"code", "message", ...}}`` with fixed,
generic messages. Exception text, SQL, stack traces and echoed input values
are never included. Unexpected errors are logged server-side (type only in
production) and answered with a generic 500.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from types import MappingProxyType

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.errors import AppError, Forbidden, InternalError, InvalidRequest, NotFound, RateLimited
from app.middleware import SECURITY_HEADERS

logger = logging.getLogger("ieogagi.error")

VALUE_ERROR_PREFIX = "Value error, "
SAFE_FIELD_PART = re.compile(r"[A-Za-z_][A-Za-z0-9_]{0,40}|[0-9]{1,4}")
MAX_REPORTED_FIELDS = 10
STATUS_TO_ERROR: Mapping[int, type[AppError]] = MappingProxyType({403: Forbidden, 404: NotFound})


def _json(error: AppError) -> JSONResponse:
    return JSONResponse(error.to_body(), status_code=error.status_code)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return _json(exc)


def _safe_field_path(location: tuple) -> str:
    """Join a validation error location, keeping only identifier-like parts.

    Unknown keys sent by the client are not echoed back verbatim: the path is
    cut at the first part that is not a plain identifier or list index.
    """
    parts: list[str] = []
    for part in location:
        text = str(part)
        if not SAFE_FIELD_PART.fullmatch(text):
            break
        parts.append(text)
    return ".".join(parts) or "body"


async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields: list[str] = []
    messages: list[str] = []
    for error in exc.errors()[:MAX_REPORTED_FIELDS]:
        fields.append(_safe_field_path(tuple(error.get("loc", ()))))
        # Only messages we wrote ourselves (field validators) are passed on;
        # pydantic's built-in messages and the rejected input are not echoed.
        message = str(error.get("msg", ""))
        if error.get("type") == "value_error" and message.startswith(VALUE_ERROR_PREFIX):
            messages.append(message.removeprefix(VALUE_ERROR_PREFIX))
    detail = InvalidRequest(messages[0] if messages else None, fields=fields)
    return _json(detail)


async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    # FastAPI wraps errors raised while reading the body (e.g. our streaming
    # size limit) in a generic 400; answer with the original AppError instead.
    if isinstance(exc.__cause__, AppError):
        return _json(exc.__cause__)
    error_type = STATUS_TO_ERROR.get(exc.status_code)
    if error_type is not None:
        return _json(error_type())
    if exc.status_code == 405:
        return _json(NotFound())
    if 400 <= exc.status_code < 500:
        return _json(InvalidRequest())
    return _json(InternalError())


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning("rate_limited", extra={"event": "rate_limited"})
    return _json(RateLimited())


async def database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.error("database_error", exc_info=exc, extra={"error_type": type(exc).__name__})
    return _json(InternalError())


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_error", exc_info=exc, extra={"error_type": type(exc).__name__})
    response = _json(InternalError())
    # This handler runs in Starlette's outermost layer, outside our header
    # middleware, so the security headers are added here explicitly.
    response.headers.update(SECURITY_HEADERS)
    return response


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_exception_handler(SQLAlchemyError, database_error_handler)
    # Last resort for anything unexpected: generic 500, details stay in server logs.
    app.add_exception_handler(Exception, unhandled_error_handler)
