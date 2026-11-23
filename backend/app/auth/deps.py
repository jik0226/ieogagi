"""Authentication dependency: resolve the session cookie to an active user."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.auth.cookies import SESSION_REFRESH_STATE
from app.auth.sessions import touch_session
from app.clock import ClockDep
from app.db import DbSession
from app.errors import Unauthenticated
from app.models import AppUser


def get_current_user(request: Request, db: DbSession, clock: ClockDep) -> AppUser:
    settings = request.app.state.settings
    token = request.cookies.get(settings.cookie_name, "")
    user_id = touch_session(
        db, token=token, settings=settings, key=request.app.state.secrets.session_key, clock=clock
    )
    if user_id is None:
        raise Unauthenticated
    user = db.get(AppUser, user_id)
    if user is None or user.disabled_at is not None:
        raise Unauthenticated
    db.commit()
    request.state.user_id = user.id
    # Ask SessionCookieRefreshMiddleware to renew the cookie's Max-Age (sliding idle window).
    setattr(request.state, SESSION_REFRESH_STATE, True)
    return user


CurrentUser = Annotated[AppUser, Depends(get_current_user)]
