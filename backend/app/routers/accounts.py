"""Account routes: invites, user list, disabling (F1, F9)."""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.audit.writer import AuditorDep
from app.authz.deps import StaffUser, route_template
from app.clock import ClockDep
from app.db import DbSession
from app.models import Role
from app.schemas.auth import InviteCreatedOut, InviteCreateRequest, UserSummaryOut
from app.schemas.common import IdPath
from app.services.accounts import create_invite, disable_user, list_users

router = APIRouter(prefix="/api", tags=["accounts"])


@router.post("/invites", response_model=InviteCreatedOut, status_code=status.HTTP_201_CREATED)
def create_invite_route(
    request: Request,
    payload: InviteCreateRequest,
    user: StaffUser,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> InviteCreatedOut:
    return create_invite(
        db,
        actor=user,
        role=Role(payload.role),
        settings=request.app.state.settings,
        key=request.app.state.secrets.session_key,
        clock=clock,
        auditor=auditor,
        attempted=route_template(request),
    )


@router.get("/users", response_model=list[UserSummaryOut])
def list_users_route(user: StaffUser, db: DbSession, clock: ClockDep) -> list[UserSummaryOut]:
    return list_users(db, actor=user, today=clock.today_kst())


@router.post("/users/{user_id}/disable", response_model=UserSummaryOut)
def disable_user_route(
    request: Request,
    user_id: IdPath,
    user: StaffUser,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> UserSummaryOut:
    return disable_user(
        db,
        actor=user,
        target_id=user_id,
        clock=clock,
        auditor=auditor,
        attempted=route_template(request),
    )
