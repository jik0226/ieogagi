"""Retention purge: delete long-dead session rows and finished invite rows.

Policy (team lead decision, 2026-10-13): expired or revoked sessions and used
or expired invites are deleted once they are older than the retention window
(30 days by default and never less). Login, logout, signup and invite facts are
already recorded in ``audit_log``, so these rows have no further use.

The function never commits; the caller owns the transaction. It needs DELETE
on ``user_session`` and ``invite``, which the application database role
deliberately does not have, so it must run under the owner role.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import ColumnElement, delete, func, or_, select
from sqlalchemy.orm import Session

from app.models import Invite, UserSession

MIN_RETENTION_DAYS = 30
# Upper bound keeps the cutoff arithmetic far from datetime overflow.
MAX_RETENTION_DAYS = 3650


@dataclass(frozen=True)
class PurgeResult:
    """Number of rows deleted (or, in a dry run, that would be deleted)."""

    sessions: int
    invites: int


def _dead_sessions(cutoff: datetime, idle_minutes: int) -> ColumnElement[bool]:
    """Sessions whose dead-since time is before ``cutoff``.

    A session is dead since the earliest of ``revoked_at`` (if set),
    ``expires_at`` and ``last_seen_at + idle timeout``. "The earliest is before
    the cutoff" is the same as "any of them is before the cutoff", and unlike
    interval arithmetic in SQL this form stays valid for NULL ``revoked_at``.
    """
    idle_cutoff = cutoff - timedelta(minutes=idle_minutes)
    return or_(
        UserSession.revoked_at < cutoff,
        UserSession.expires_at < cutoff,
        UserSession.last_seen_at < idle_cutoff,
    )


def _finished_invites(cutoff: datetime) -> ColumnElement[bool]:
    """Invites finished before ``cutoff``: used_at if set, otherwise expires_at."""
    return func.coalesce(Invite.used_at, Invite.expires_at) < cutoff


def _purge(
    db: Session, model: type[UserSession | Invite], condition: ColumnElement[bool], *, dry_run: bool
) -> int:
    """Delete the ``model`` rows matching ``condition`` or, in a dry run, count them."""
    if dry_run:
        counted = select(func.count()).select_from(model).where(condition)
        return db.execute(counted).scalar_one()
    result = db.execute(delete(model).where(condition).execution_options(synchronize_session=False))
    return result.rowcount or 0


def purge_stale_rows(
    db: Session,
    now: datetime,
    *,
    retention_days: int = MIN_RETENTION_DAYS,
    idle_minutes: int,
    dry_run: bool = False,
) -> PurgeResult:
    """Delete sessions and invites that have been finished for over ``retention_days``.

    ``idle_minutes`` is the session idle timeout, needed to know when an
    unrevoked, unexpired session went idle-dead. With ``dry_run`` the matching
    rows are only counted. Rows are removed with bulk DELETE statements, so
    ORM objects of these tables already loaded in ``db`` are not refreshed.
    """
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    if not MIN_RETENTION_DAYS <= retention_days <= MAX_RETENTION_DAYS:
        raise ValueError(
            f"retention_days must be between {MIN_RETENTION_DAYS} and {MAX_RETENTION_DAYS}"
        )
    if idle_minutes < 1:
        raise ValueError("idle_minutes must be at least 1")

    cutoff = now - timedelta(days=retention_days)
    sessions = _purge(db, UserSession, _dead_sessions(cutoff, idle_minutes), dry_run=dry_run)
    invites = _purge(db, Invite, _finished_invites(cutoff), dry_run=dry_run)
    return PurgeResult(sessions=sessions, invites=invites)
