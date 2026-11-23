"""Authentication routes (F1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from app.audit.writer import AuditorDep
from app.auth.cookies import clear_session_cookie, set_session_cookie
from app.auth.deps import CurrentUser
from app.auth.sessions import issue_session, revoke_session
from app.authz.deps import public_endpoint
from app.clock import ClockDep
from app.db import DbSession
from app.models import AppUser
from app.schemas.auth import (
    InviteVerifyOut,
    InviteVerifyRequest,
    LoginRequest,
    MeOut,
    SignupRequest,
)
from app.security.ratelimit import INVITE_LIMIT, LOGIN_LIMIT, SIGNUP_LIMIT, limiter
from app.services.auth_service import authenticate, signup, verify_invite

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/invites/verify", response_model=InviteVerifyOut, dependencies=[Depends(public_endpoint)]
)
@limiter.limit(INVITE_LIMIT)
def verify_invite_route(
    request: Request, payload: InviteVerifyRequest, db: DbSession, clock: ClockDep
) -> InviteVerifyOut:
    return verify_invite(
        db, code=payload.code, key=request.app.state.secrets.session_key, clock=clock
    )


@router.post(
    "/signup",
    response_model=MeOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(public_endpoint)],
)
@limiter.limit(SIGNUP_LIMIT)
def signup_route(
    request: Request, payload: SignupRequest, db: DbSession, clock: ClockDep, auditor: AuditorDep
) -> MeOut:
    user = signup(
        db, payload=payload, key=request.app.state.secrets.session_key, clock=clock, auditor=auditor
    )
    db.refresh(user)
    return MeOut.model_validate(user)


@router.post("/login", response_model=MeOut, dependencies=[Depends(public_endpoint)])
@limiter.limit(LOGIN_LIMIT)
def login_route(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> MeOut:
    settings = request.app.state.settings
    user = authenticate(
        db,
        login_id=payload.login_id,
        password=payload.password,
        settings=settings,
        clock=clock,
        auditor=auditor,
    )
    # Never keep a session token the browser brought in from before this login.
    revoke_session(
        db,
        token=request.cookies.get(settings.cookie_name, ""),
        key=request.app.state.secrets.session_key,
        clock=clock,
    )
    token = issue_session(
        db, user=user, settings=settings, key=request.app.state.secrets.session_key, clock=clock
    )
    auditor.stage(db, actor=user, action="auth.login", target_type="user", target_id=user.id)
    db.commit()
    set_session_cookie(response, settings, token)
    return MeOut.model_validate(user)


@router.post(
    "/logout", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(public_endpoint)]
)
def logout_route(request: Request, db: DbSession, clock: ClockDep, auditor: AuditorDep) -> Response:
    """Always succeeds: revokes the session if it is still active and clears the cookie,
    so an expired session can still log out cleanly."""
    settings = request.app.state.settings
    user_id = revoke_session(
        db,
        token=request.cookies.get(settings.cookie_name, ""),
        key=request.app.state.secrets.session_key,
        clock=clock,
    )
    if user_id is not None:
        auditor.stage(
            db,
            actor=db.get(AppUser, user_id),
            action="auth.logout",
            target_type="user",
            target_id=user_id,
        )
    db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings)
    return response


@router.get("/me", response_model=MeOut)
def me_route(user: CurrentUser) -> MeOut:
    return MeOut.model_validate(user)
