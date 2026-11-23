"""DB-backed sessions: issue, validate-and-touch, revoke.

Validation and the idle-timeout refresh happen in ONE conditional UPDATE, so
there is no gap between checking a session and using it (no TOCTOU), and
permissions are never cached in the token: the user row is re-read on every
request, so disabling an account takes effect immediately.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.clock import Clock
from app.config import Settings
from app.models import AppUser, UserSession
from app.security.tokens import keyed_digest, new_session_token

SESSION_PURPOSE = "session"
MAX_TOKEN_LENGTH = 128


def _digest(key: bytes, token: str) -> str:
    return keyed_digest(key, token, purpose=SESSION_PURPOSE)


def issue_session(
    db: Session, *, user: AppUser, settings: Settings, key: bytes, clock: Clock
) -> str:
    """Create a session row and return the raw token for the cookie (shown once)."""
    token = new_session_token()
    now = clock.now()
    db.add(
        UserSession(
            token_hash=_digest(key, token),
            user_id=user.id,
            created_at=now,
            expires_at=now + timedelta(hours=settings.session_absolute_hours),
            last_seen_at=now,
        )
    )
    return token


def touch_session(
    db: Session, *, token: str, settings: Settings, key: bytes, clock: Clock
) -> int | None:
    """Return the session's user id if valid (refreshing last_seen_at), else None."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    now = clock.now()
    idle_cutoff = now - timedelta(minutes=settings.session_idle_minutes)
    stmt = (
        update(UserSession)
        .where(
            UserSession.token_hash == _digest(key, token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > now,
            UserSession.last_seen_at > idle_cutoff,
        )
        .values(last_seen_at=now)
        .returning(UserSession.user_id)
        .execution_options(synchronize_session=False)
    )
    return db.execute(stmt).scalar_one_or_none()


def revoke_session(db: Session, *, token: str, key: bytes, clock: Clock) -> int | None:
    """Revoke the session for ``token`` if it is still active; return its user id."""
    if not token or len(token) > MAX_TOKEN_LENGTH:
        return None
    return db.execute(
        update(UserSession)
        .where(UserSession.token_hash == _digest(key, token), UserSession.revoked_at.is_(None))
        .values(revoked_at=clock.now())
        .returning(UserSession.user_id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()


def revoke_all_sessions(db: Session, *, user_id: int, clock: Clock) -> int:
    result = db.execute(
        update(UserSession)
        .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=clock.now())
        .execution_options(synchronize_session=False)
    )
    return result.rowcount or 0
