"""Helpers for deterministic two-connection concurrency tests.

One side of a race runs on a held connection in the test thread: either the
real service code (through ``held_session``) or single SQL steps. The other
side is a real request on a worker thread. ``wait_until_blocked`` polls
PostgreSQL until the request is really blocked by the held connection, so a
test never passes merely because the request had not started yet.
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date

from app.audit.writer import Auditor
from app.authz.policy import ChildAccess
from app.models import AppUser, Assignment, AuditLog, Child, Record, StaffNote
from app.services.children import destroy_child
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, func, select, text
from sqlalchemy.orm import Session

from tests.factories import Factory
from tests.scenario import World

LOCK_WAIT_TIMEOUT = 5.0
POLL_INTERVAL = 0.02
# A side statement that should never wait long fails instead of hanging the run.
SIDE_LOCK_TIMEOUT = "SET LOCAL lock_timeout = '5s'"
BLOCKED_BY = (
    "SELECT count(*) FROM pg_stat_activity "
    "WHERE datname = current_database() AND :blocker = ANY(pg_blocking_pids(pid))"
)


@contextmanager
def held_connection(engine: Engine) -> Iterator[Connection]:
    """A connection with an open transaction; locks stay until ``commit()``.

    Leaving the block without committing rolls back, which releases the
    locks so a waiting request thread can finish.
    """
    with engine.connect() as conn:
        conn.execute(text(SIDE_LOCK_TIMEOUT))
        yield conn


@contextmanager
def held_session(engine: Engine) -> Iterator[tuple[Session, Connection]]:
    """A session whose ``commit()`` only releases a savepoint.

    Service code runs unchanged, but the row locks it takes stay held by the
    outer transaction: an in-flight request frozen just before COMMIT. The
    test commits (or rolls back) the returned connection to let it finish.
    """
    with held_connection(engine) as conn:
        session = Session(
            bind=conn,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
            autoflush=False,
        )
        try:
            yield session, conn
        finally:
            session.close()


def backend_pid(conn: Connection) -> int:
    pid = conn.scalar(text("SELECT pg_backend_pid()"))
    if pid is None:
        raise AssertionError("no backend pid")
    return int(pid)


def wait_until_blocked(engine: Engine, blocker: Connection, count: int = 1) -> None:
    """Return once ``count`` backends wait for a lock ``blocker`` holds, or fail."""
    pid = backend_pid(blocker)
    deadline = time.monotonic() + LOCK_WAIT_TIMEOUT
    with engine.connect() as conn:
        while True:
            waiting = conn.scalar(text(BLOCKED_BY), {"blocker": pid})
            conn.rollback()  # pg_stat_activity is a per-transaction snapshot
            if waiting is not None and waiting >= count:
                return
            if time.monotonic() > deadline:
                raise AssertionError(f"expected {count} request(s) blocked by backend {pid}")
            time.sleep(POLL_INTERVAL)


def auditor_for(factory: Factory) -> Auditor:
    return Auditor(clock=factory.clock, ip=None)


def client_for(factory: Factory, user: AppUser) -> TestClient:
    """A logged-in client for which a server error comes back as a 500 response."""
    return factory.client_for(user, raise_server_exceptions=False)


# Shared by the child destruction tests (scenario: tests/scenario.py).
SESSION_DAY = date(2026, 10, 14)
NOTHING_LEFT = {"child": 0, "record": 0, "note": 0, "assignment": 0}


def left_for_child(factory: Factory, child_id: int) -> dict[str, int]:
    def count(model: type, condition) -> int:
        return factory.db.scalar(select(func.count()).select_from(model).where(condition)) or 0

    return {
        "child": count(Child, Child.id == child_id),
        "record": count(Record, Record.child_id == child_id),
        "note": count(StaffNote, StaffNote.child_id == child_id),
        "assignment": count(Assignment, Assignment.child_id == child_id),
    }


def destroy_audits(factory: Factory) -> list[dict]:
    return list(
        factory.db.scalars(select(AuditLog.detail).where(AuditLog.action == "child.destroy"))
    )


def start_destroy(side: Session, factory: Factory, world: World) -> None:
    """Run the real destruction on a held session (locks held, not committed)."""
    access = ChildAccess(user=world.director_a, child_id=world.child.id, assignment=None)
    destroy_child(
        side, access=access, clock=factory.clock, auditor=auditor_for(factory), attempted="test"
    )


def record_row(factory: Factory, world: World, *, corrects_id: int | None, did: str) -> dict:
    """Column values for a record the current mentor writes on SESSION_DAY."""
    return {
        "child_id": world.child.id,
        "author_id": world.mentor_now.id,
        "session_date": SESSION_DAY,
        "did": did,
        "stuck": "",
        "next_step": "",
        "corrects_id": corrects_id,
        "created_at": factory.clock.now(),
    }
