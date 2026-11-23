"""Retention purge: dead session rows and finished invite rows older than 30 days.

The purge runs under the owner role (the app role has no DELETE on these
tables); rows are arranged and inspected with the admin session from conftest.
"""

from __future__ import annotations

import logging
import secrets
import sys
from collections.abc import Iterator
from datetime import timedelta

import pytest
from app.cli import cleanup_cmd
from app.models import AppUser, Invite, Role, UserSession
from app.services.retention import PurgeResult, purge_stale_rows
from sqlalchemy import Engine, select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from tests.conftest import _role_engine
from tests.factories import Factory
from tests.fixed_clock import FixedClock

INSUFFICIENT_PRIVILEGE = "42501"


@pytest.fixture
def owner_engine(db: Session) -> Iterator[Engine]:
    # Depends on ``db`` so the tables are truncated before the test arranges rows.
    engine = _role_engine("ieogagi_owner")
    yield engine
    engine.dispose()


@pytest.fixture
def owner_db(owner_engine: Engine) -> Iterator[Session]:
    with Session(owner_engine) as session:
        yield session


@pytest.fixture
def idle(factory: Factory) -> int:
    return factory.settings.session_idle_minutes


@pytest.fixture
def user(factory: Factory) -> AppUser:
    return factory.user(factory.center(), Role.MENTOR)


def _days(count: int) -> timedelta:
    return timedelta(days=count)


def _session(
    factory: Factory,
    user: AppUser,
    *,
    expires_in: timedelta = timedelta(hours=1),
    last_seen_ago: timedelta = timedelta(minutes=1),
    revoked_ago: timedelta | None = None,
) -> int:
    """Insert a session row relative to the fixed clock and return its id."""
    now = factory.clock.now()
    row = UserSession(
        token_hash=secrets.token_hex(32),
        user_id=user.id,
        created_at=now - _days(60),
        expires_at=now + expires_in,
        last_seen_at=now - last_seen_ago,
        revoked_at=None if revoked_ago is None else now - revoked_ago,
    )
    factory.db.add(row)
    factory.db.commit()
    return row.id


def _invite(
    factory: Factory,
    user: AppUser,
    *,
    expires_in: timedelta,
    used_ago: timedelta | None = None,
) -> int:
    """Insert an invite row relative to the fixed clock and return its id."""
    now = factory.clock.now()
    row = Invite(
        code_hash=secrets.token_hex(32),
        center_id=user.center_id,
        role=Role.MENTOR.value,
        created_by=user.id,
        created_at=now - _days(60),
        expires_at=now + expires_in,
        used_at=None if used_ago is None else now - used_ago,
        used_by=None if used_ago is None else user.id,
    )
    factory.db.add(row)
    factory.db.commit()
    return row.id


def _purge(owner_db: Session, clock: FixedClock, idle: int, **kwargs) -> PurgeResult:
    result = purge_stale_rows(owner_db, clock.now(), idle_minutes=idle, **kwargs)
    owner_db.commit()
    return result


def _remaining(db: Session, model: type[UserSession | Invite]) -> set[int]:
    db.rollback()  # end the open transaction so the read is current
    return set(db.scalars(select(model.id)))


def test_revoked_session_is_deleted_only_after_30_days(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser
) -> None:
    # Expiry and last_seen stay recent, so only revoked_at decides.
    _session(factory, user, revoked_ago=_days(31))
    recent = _session(factory, user, revoked_ago=_days(29))
    result = _purge(owner_db, clock, idle)
    assert result == PurgeResult(sessions=1, invites=0)
    assert _remaining(factory.db, UserSession) == {recent}


def test_cutoff_is_exclusive(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser
) -> None:
    on_cutoff = _session(factory, user, revoked_ago=_days(30))
    _session(factory, user, revoked_ago=_days(30) + timedelta(seconds=1))
    _purge(owner_db, clock, idle)
    assert _remaining(factory.db, UserSession) == {on_cutoff}


def test_expired_session_is_deleted_and_active_session_is_kept(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser
) -> None:
    _session(factory, user, expires_in=-_days(31), last_seen_ago=_days(0))
    expired_recently = _session(factory, user, expires_in=-_days(29), last_seen_ago=_days(0))
    active = _session(factory, user)
    result = _purge(owner_db, clock, idle)
    assert result.sessions == 1
    assert _remaining(factory.db, UserSession) == {expired_recently, active}


def test_idle_expired_session_is_deleted(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser
) -> None:
    # expires_at is in the future: only last_seen_at + idle timeout can kill these.
    idle_for_30_days = _days(30) + timedelta(minutes=idle)
    minute = timedelta(minutes=1)
    _session(factory, user, last_seen_ago=idle_for_30_days + minute)
    idle_under_30_days = _session(factory, user, last_seen_ago=idle_for_30_days - minute)
    result = _purge(owner_db, clock, idle)
    assert result.sessions == 1
    assert _remaining(factory.db, UserSession) == {idle_under_30_days}


def test_finished_invites_are_deleted_and_open_or_recent_ones_are_kept(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser
) -> None:
    _invite(factory, user, expires_in=-_days(40), used_ago=_days(31))
    _invite(factory, user, expires_in=-_days(31))
    open_invite = _invite(factory, user, expires_in=timedelta(hours=72))
    used_recently = _invite(factory, user, expires_in=-_days(8), used_ago=_days(10))
    result = _purge(owner_db, clock, idle)
    assert result == PurgeResult(sessions=0, invites=2)
    assert _remaining(factory.db, Invite) == {open_invite, used_recently}


def test_used_at_takes_precedence_over_expires_at(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser
) -> None:
    # An invite counts as finished when it was used, even if its expiry is older.
    used_recently = _invite(factory, user, expires_in=-_days(40), used_ago=_days(10))
    assert _purge(owner_db, clock, idle).invites == 0
    assert _remaining(factory.db, Invite) == {used_recently}


def test_dry_run_counts_the_same_rows_but_deletes_nothing(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser
) -> None:
    for ago in (_days(31), _days(45)):
        _session(factory, user, revoked_ago=ago)
    _session(factory, user)
    _invite(factory, user, expires_in=-_days(31))
    _invite(factory, user, expires_in=timedelta(hours=72))
    sessions_before = _remaining(factory.db, UserSession)
    invites_before = _remaining(factory.db, Invite)

    dry = _purge(owner_db, clock, idle, dry_run=True)
    assert dry == PurgeResult(sessions=2, invites=1)
    assert _remaining(factory.db, UserSession) == sessions_before
    assert _remaining(factory.db, Invite) == invites_before

    assert _purge(owner_db, clock, idle) == dry
    assert len(_remaining(factory.db, UserSession)) == 1
    assert len(_remaining(factory.db, Invite)) == 1


def test_purge_does_not_commit(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser
) -> None:
    _session(factory, user, revoked_ago=_days(31))
    assert purge_stale_rows(owner_db, clock.now(), idle_minutes=idle) == PurgeResult(1, 0)
    owner_db.rollback()
    assert len(_remaining(factory.db, UserSession)) == 1


@pytest.mark.parametrize("days", [29, 0, -1, 3651])
def test_retention_outside_allowed_range_is_rejected(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser, days: int
) -> None:
    kept = _session(factory, user, revoked_ago=_days(40))
    with pytest.raises(ValueError, match="retention_days"):
        purge_stale_rows(owner_db, clock.now(), retention_days=days, idle_minutes=idle)
    assert _remaining(factory.db, UserSession) == {kept}


def test_naive_now_and_invalid_idle_are_rejected(owner_db: Session, clock: FixedClock) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        purge_stale_rows(owner_db, clock.now().replace(tzinfo=None), idle_minutes=10)
    with pytest.raises(ValueError, match="idle_minutes"):
        purge_stale_rows(owner_db, clock.now(), idle_minutes=0)


def test_longer_retention_keeps_rows_inside_the_window(
    factory: Factory, owner_db: Session, clock: FixedClock, idle: int, user: AppUser
) -> None:
    in_window = _session(factory, user, revoked_ago=_days(45))
    _session(factory, user, revoked_ago=_days(91))
    assert _purge(owner_db, clock, idle, retention_days=90).sessions == 1
    assert _remaining(factory.db, UserSession) == {in_window}


def test_app_role_cannot_delete_sessions_or_invites(
    app_engine: Engine, factory: Factory, user: AppUser
) -> None:
    """Documents why cleanup runs as the owner role: the app role has no DELETE here."""
    session_id = _session(factory, user, revoked_ago=_days(60))
    invite_id = _invite(factory, user, expires_in=-_days(60))
    with app_engine.connect() as conn:
        for statement in ("DELETE FROM user_session", "DELETE FROM invite"):
            with pytest.raises(ProgrammingError) as caught:
                conn.execute(text(statement))
            assert caught.value.orig.sqlstate == INSUFFICIENT_PRIVILEGE
            conn.rollback()
    assert _remaining(factory.db, UserSession) == {session_id}
    assert _remaining(factory.db, Invite) == {invite_id}


def _run_cli(
    monkeypatch: pytest.MonkeyPatch, owner_engine: Engine, clock: FixedClock, *args: str
) -> None:
    monkeypatch.setattr(sys, "argv", ["ieogagi-cleanup", *args])
    monkeypatch.setattr(cleanup_cmd, "owner_engine", lambda: owner_engine)
    monkeypatch.setattr(cleanup_cmd, "Clock", lambda: clock)
    cleanup_cmd.cleanup_command()


def test_cli_dry_run_reports_and_real_run_deletes(
    factory: Factory,
    owner_engine: Engine,
    clock: FixedClock,
    user: AppUser,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _session(factory, user, revoked_ago=_days(31))
    _invite(factory, user, expires_in=-_days(31))
    with caplog.at_level(logging.INFO, logger="ieogagi.cli"):
        _run_cli(monkeypatch, owner_engine, clock, "--dry-run")
        _run_cli(monkeypatch, owner_engine, clock)
    messages = [record.getMessage() for record in caplog.records if record.name == "ieogagi.cli"]
    assert messages == [
        "Dry run: would delete 1 sessions and 1 invites older than 30 days",
        "Deleted 1 sessions and 1 invites older than 30 days",
    ]
    assert not _remaining(factory.db, UserSession)
    assert not _remaining(factory.db, Invite)


@pytest.mark.parametrize("days", ["29", "abc", "3651"])
def test_cli_rejects_retention_outside_allowed_range(
    days: str,
    owner_engine: Engine,
    clock: FixedClock,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as caught:
        _run_cli(monkeypatch, owner_engine, clock, "--days", days)
    assert caught.value.code == 2
    assert "--days" in capsys.readouterr().err
