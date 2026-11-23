"""Invite issuing, user listing and account disabling (director/staff)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from types import MappingProxyType

from sqlalchemy import and_, exists, select, update
from sqlalchemy.orm import Session

from app.audit.writer import Auditor
from app.auth.sessions import revoke_all_sessions
from app.authz.policy import deny
from app.clock import Clock
from app.config import Settings
from app.errors import Conflict
from app.models import AppUser, Assignment, Invite, Role
from app.schemas.auth import InviteCreatedOut, UserSummaryOut
from app.security.tokens import new_invite_code
from app.services.auth_service import invite_digest

# Who may act on whom: director → staff and mentors; staff → mentors only.
# Read-only so no caller can widen these authorization rules at runtime.
INVITABLE_ROLES: Mapping[Role, frozenset[Role]] = MappingProxyType(
    {Role.DIRECTOR: frozenset({Role.STAFF, Role.MENTOR}), Role.STAFF: frozenset({Role.MENTOR})}
)
DISABLEABLE_ROLES = INVITABLE_ROLES
# Upper bounds on list sizes: every list query has a LIMIT (no unbounded reads).
USER_LIST_LIMIT = 1000


def create_invite(
    db: Session,
    *,
    actor: AppUser,
    role: Role,
    settings: Settings,
    key: bytes,
    clock: Clock,
    auditor: Auditor,
    attempted: str,
) -> InviteCreatedOut:
    if role not in INVITABLE_ROLES.get(actor.role_enum, frozenset()):
        raise deny(
            auditor,
            db,
            user=actor,
            attempted=attempted,
            target_type="invite",
            target_id=None,
            detail={"reason": "role", "invite_role": role.value},
        )
    code = new_invite_code()
    now = clock.now()
    invite = Invite(
        code_hash=invite_digest(key, code),
        center_id=actor.center_id,
        role=role.value,
        created_by=actor.id,
        created_at=now,
        expires_at=now + timedelta(hours=settings.invite_valid_hours),
    )
    db.add(invite)
    db.flush()
    auditor.stage(
        db,
        actor=actor,
        action="invite.create",
        target_type="invite",
        target_id=invite.id,
        detail={"role": role.value},
    )
    db.commit()
    return InviteCreatedOut(code=code, role=role.value, expires_at=invite.expires_at)


def _assignment_ended_expr(today: date):
    """Active mentor who had assignments but none current or upcoming."""
    had_any = exists().where(Assignment.mentor_id == AppUser.id)
    has_live = exists().where(
        and_(
            Assignment.mentor_id == AppUser.id,
            Assignment.revoked_at.is_(None),
            Assignment.end_date >= today,
        )
    )
    return and_(
        AppUser.role == Role.MENTOR.value,
        AppUser.disabled_at.is_(None),
        had_any,
        ~has_live,
    )


def list_users(db: Session, *, actor: AppUser, today: date) -> list[UserSummaryOut]:
    rows = db.execute(
        select(AppUser, _assignment_ended_expr(today).label("ended"))
        .where(AppUser.center_id == actor.center_id)
        .order_by(AppUser.role, AppUser.display_name, AppUser.id)
        .limit(USER_LIST_LIMIT)
    ).all()
    return [
        UserSummaryOut(
            id=user.id,
            login_id=user.login_id,
            display_name=user.display_name,
            role=user.role,
            disabled_at=user.disabled_at,
            assignment_ended=bool(ended),
        )
        for user, ended in rows
    ]


def disable_user(
    db: Session,
    *,
    actor: AppUser,
    target_id: int,
    clock: Clock,
    auditor: Auditor,
    attempted: str,
) -> UserSummaryOut:
    target = db.scalar(
        select(AppUser).where(AppUser.id == target_id, AppUser.center_id == actor.center_id)
    )
    allowed = DISABLEABLE_ROLES.get(actor.role_enum, frozenset())
    if target is None or target.id == actor.id or target.role_enum not in allowed:
        raise deny(
            auditor,
            db,
            user=actor,
            attempted=attempted,
            target_type="user",
            target_id=target_id,
            detail={"reason": "not_permitted_target"},
        )
    disabled = db.execute(
        update(AppUser)
        .where(AppUser.id == target.id, AppUser.disabled_at.is_(None))
        .values(disabled_at=clock.now())
        .returning(AppUser.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if disabled is None:
        raise Conflict("이미 비활성화된 계정입니다.")
    revoked = revoke_all_sessions(db, user_id=target.id, clock=clock)
    auditor.stage(
        db,
        actor=actor,
        action="user.disable",
        target_type="user",
        target_id=target.id,
        detail={"revoked_sessions": revoked},
    )
    db.commit()
    db.refresh(target)
    return UserSummaryOut(
        id=target.id,
        login_id=target.login_id,
        display_name=target.display_name,
        role=target.role,
        disabled_at=target.disabled_at,
        assignment_ended=False,
    )
