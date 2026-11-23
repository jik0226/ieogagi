"""Invite verification, signup and password login."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import case, exists, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.writer import Auditor
from app.clock import Clock
from app.config import Settings
from app.errors import Conflict, LoginFailed, NotFound
from app.models import AppUser, AuditResult, Center, Invite
from app.schemas.auth import InviteVerifyOut, SignupRequest
from app.security.passwords import hash_password, needs_rehash, spend_equal_time, verify_password
from app.security.tokens import keyed_digest

INVITE_PURPOSE = "invite"
INVALID_INVITE_MESSAGE = "초대 코드가 올바르지 않거나 만료되었습니다."


def invite_digest(key: bytes, code: str) -> str:
    return keyed_digest(key, code, purpose=INVITE_PURPOSE)


def _issuer_disabled():
    """True when the invite's issuer has been disabled since issuing it.

    A code dies with its issuer's authority, checked where the code is used,
    so no disabling path has to remember to close invites. CLI-issued
    director invites have no issuer (created_by NULL) and are unaffected.
    """
    return exists().where(AppUser.id == Invite.created_by, AppUser.disabled_at.is_not(None))


def verify_invite(db: Session, *, code: str, key: bytes, clock: Clock) -> InviteVerifyOut:
    row = db.execute(
        select(Invite.role, Invite.expires_at, Center.name)
        .join(Center, Center.id == Invite.center_id)
        .where(
            Invite.code_hash == invite_digest(key, code),
            Invite.used_at.is_(None),
            Invite.expires_at > clock.now(),
            ~_issuer_disabled(),
        )
    ).one_or_none()
    if row is None:
        raise NotFound(INVALID_INVITE_MESSAGE)
    return InviteVerifyOut(role=row.role, center_name=row.name, expires_at=row.expires_at)


def signup(
    db: Session, *, payload: SignupRequest, key: bytes, clock: Clock, auditor: Auditor
) -> AppUser:
    now = clock.now()
    digest = invite_digest(key, payload.code)
    # Consume the invite with one conditional UPDATE: two concurrent signups
    # with the same code cannot both succeed (no check-then-use gap).
    consumed = db.execute(
        update(Invite)
        .where(
            Invite.code_hash == digest,
            Invite.used_at.is_(None),
            Invite.expires_at > now,
            ~_issuer_disabled(),
        )
        .values(used_at=now)
        .returning(Invite.id, Invite.center_id, Invite.role)
        .execution_options(synchronize_session=False)
    ).one_or_none()
    if consumed is None:
        _log_refused_invite(db, auditor, digest=digest, now=now)
        raise NotFound(INVALID_INVITE_MESSAGE)
    user = AppUser(
        center_id=consumed.center_id,
        login_id=payload.login_id,
        display_name=payload.display_name,
        role=consumed.role,
        password_hash=hash_password(payload.password),
        failed_count=0,
        created_at=now,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()  # also restores the invite, so the code can be retried
        raise Conflict("이미 사용 중인 아이디입니다.") from exc
    db.execute(
        update(Invite)
        .where(Invite.id == consumed.id)
        .values(used_by=user.id)
        .execution_options(synchronize_session=False)
    )
    auditor.stage(
        db,
        actor=user,
        action="auth.signup",
        target_type="user",
        target_id=user.id,
        detail={"role": consumed.role, "invite_id": consumed.id},
    )
    db.commit()
    return user


def _log_refused_invite(db: Session, auditor: Auditor, *, digest: str, now: datetime) -> None:
    """One audit row per refused signup; the response is the same either way.

    A live code refused only because its issuer was disabled is logged to that
    center as denied, so staff can see a former colleague's code being tried.
    """
    blocked = db.execute(
        select(Invite.id, Invite.center_id).where(
            Invite.code_hash == digest,
            Invite.used_at.is_(None),
            Invite.expires_at > now,
            _issuer_disabled(),
        )
    ).one_or_none()
    if blocked is None:
        auditor.write_now(
            db,
            actor=None,
            action="auth.signup",
            result=AuditResult.FAILURE,
            detail={"reason": "invalid_invite"},
        )
        return
    auditor.write_now(
        db,
        actor=None,
        action="auth.signup",
        result=AuditResult.DENIED,
        target_type="invite",
        target_id=blocked.id,
        detail={"reason": "issuer_disabled"},
        center_id=blocked.center_id,
    )


def _reserve_attempt(db: Session, *, user_id: int, settings: Settings, clock: Clock) -> bool:
    """Atomically claim one login attempt BEFORE the password is checked.

    One conditional UPDATE counts the attempt and, on the Nth one, sets the
    lock. Concurrent requests cannot all slip past the limit: once the lock
    is set, the WHERE clause matches no row and the attempt is refused
    without verifying the password. Returns False if no attempt is allowed.
    """
    now = clock.now()
    reached = AppUser.failed_count + 1 >= settings.login_max_failures
    claimed = db.execute(
        update(AppUser)
        .where(
            AppUser.id == user_id,
            AppUser.disabled_at.is_(None),
            or_(AppUser.locked_until.is_(None), AppUser.locked_until <= now),
        )
        .values(
            failed_count=case((reached, 0), else_=AppUser.failed_count + 1),
            locked_until=case(
                (reached, now + timedelta(minutes=settings.login_lock_minutes)), else_=None
            ),
        )
        .returning(AppUser.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    db.commit()  # make the claim visible to concurrent requests before argon2 runs
    return claimed is not None


def _refusal_reason(db: Session, *, user_id: int) -> str:
    """Why ``_reserve_attempt`` claimed no row, read from the row as it is now.

    The user object was loaded before the claim; the account may have been
    disabled in between, which must not be logged as a lockout.
    """
    disabled_at = db.scalar(select(AppUser.disabled_at).where(AppUser.id == user_id))
    return "disabled" if disabled_at is not None else "locked"


def _deny_login(
    db: Session, auditor: Auditor, *, user: AppUser | None, reason: str, result: AuditResult
) -> LoginFailed:
    auditor.write_now(
        db,
        actor=user,
        action="auth.login",
        result=result,
        target_type="user" if user else None,
        target_id=user.id if user else None,
        detail={"reason": reason},
    )
    return LoginFailed()


def authenticate(
    db: Session, *, login_id: str, password: str, settings: Settings, clock: Clock, auditor: Auditor
) -> AppUser:
    user = db.scalar(select(AppUser).where(AppUser.login_id == login_id))
    if user is None:
        spend_equal_time(password)
        raise _deny_login(
            db, auditor, user=None, reason="unknown_account", result=AuditResult.FAILURE
        )
    if not _reserve_attempt(db, user_id=user.id, settings=settings, clock=clock):
        spend_equal_time(password)
        reason = _refusal_reason(db, user_id=user.id)
        raise _deny_login(db, auditor, user=user, reason=reason, result=AuditResult.DENIED)
    if not verify_password(user.password_hash, password):
        raise _deny_login(db, auditor, user=user, reason="bad_password", result=AuditResult.FAILURE)
    values: dict[str, object] = {"failed_count": 0, "locked_until": None}
    if needs_rehash(user.password_hash):
        values["password_hash"] = hash_password(password)
    db.execute(
        update(AppUser)
        .where(AppUser.id == user.id)
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    return user
