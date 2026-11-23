"""Session cookie: HttpOnly, Secure, SameSite=Strict, Max-Age = server idle timeout.

Security diagnosis 02.10 (information exposure through a cookie kept on the user's
disk): the cookie used to have no Max-Age at all. Browsers that restore the previous
session ("continue where you left off") then keep such a cookie with no client-side
limit, which on a shared center PC is exactly the persistent cookie the item warns
about. The cookie now carries an explicit Max-Age equal to the server idle timeout
(default 10 minutes, capped at 60 minutes by ``Settings``) and is re-issued on every
authenticated response (``SessionCookieRefreshMiddleware``), so the browser deletes it
no later than the server would reject it. The server still enforces idle and absolute
(8 hours) expiry independently, so a copied cookie is useless after either limit.

Secure is not configurable on purpose: browsers treat http://localhost as a secure
context, so local development works without a downgrade switch that could leak into
production. The default name uses the ``__Host-`` prefix, which browsers accept only
with Secure, Path=/ and no Domain (blocks cookie injection from sibling subdomains).
"""

from __future__ import annotations

from fastapi import Response

from app.config import Settings

# request.state key set by get_current_user once the session is verified (read by
# SessionCookieRefreshMiddleware). A flag only: the token itself is never copied there.
SESSION_REFRESH_STATE = "session_cookie_refresh"


def session_cookie_max_age(settings: Settings) -> int:
    """Cookie lifetime in seconds: the idle timeout (at most 3600 s by config bounds)."""
    return settings.session_idle_minutes * 60


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=session_cookie_max_age(settings),
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.cookie_name, path="/", secure=True, httponly=True, samesite="strict"
    )
