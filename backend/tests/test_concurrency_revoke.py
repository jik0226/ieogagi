"""Assignment revoke racing a mentor's record create (shared lock on the assignment).

No record may be created after a revoke committed: either the create commits
first and the revoke waits for its FOR SHARE lock, or the create waits for
the revoke and then sees the revoked assignment (403).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from app.authz.policy import authorize_child
from app.models import Assignment, Record, Role
from app.schemas.records import RecordCreateRequest
from app.services.assignments import revoke_assignment
from app.services.records import create_record
from sqlalchemy import func, select

from tests.concurrency import auditor_for, client_for, held_session, wait_until_blocked
from tests.factories import Factory
from tests.scenario import World, build_world

SESSION_DAY = date(2026, 10, 14)
RECORD_BODY = {"session_date": SESSION_DAY.isoformat(), "did": "새 기록"}


@pytest.fixture
def world(factory: Factory) -> World:
    return build_world(factory)


def _new_records(factory: Factory, world: World) -> int:
    count = factory.db.scalar(
        select(func.count())
        .select_from(Record)
        .where(Record.child_id == world.child.id, Record.author_id == world.mentor_now.id)
    )
    return count or 0


def test_revoke_waits_for_an_in_flight_record_create(
    app_engine, admin_engine, factory: Factory, world: World
) -> None:
    staff = client_for(factory, world.staff_a)
    mentor = client_for(factory, world.mentor_now)
    revoke_url = f"/api/assignments/{world.assignment_now.id}/revoke"
    with ThreadPoolExecutor(max_workers=1) as pool, held_session(app_engine) as (side, conn):
        access = authorize_child(
            side,
            user=world.mentor_now,
            child_id=world.child.id,
            today=factory.clock.today_kst(),
            auditor=auditor_for(factory),
            allowed_roles=frozenset({Role.MENTOR}),
            attempted="test",
            lock=True,
        )
        create_record(
            side,
            access=access,
            payload=RecordCreateRequest(session_date=SESSION_DAY, did="새 기록"),
            clock=factory.clock,
            auditor=auditor_for(factory),
        )
        pending = pool.submit(staff.post, revoke_url)
        wait_until_blocked(admin_engine, conn)  # the revoke waits for the create's FOR SHARE
        conn.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 200
    assert response.json()["status"] == "revoked"
    assert _new_records(factory, world) == 1  # committed before the revoke could
    late = mentor.post(f"/api/children/{world.child.id}/records", json=RECORD_BODY)
    assert late.status_code == 403
    assert _new_records(factory, world) == 1


def test_record_create_waits_for_a_revoke_then_is_refused(
    app_engine, admin_engine, factory: Factory, world: World
) -> None:
    mentor = client_for(factory, world.mentor_now)
    with ThreadPoolExecutor(max_workers=1) as pool, held_session(app_engine) as (side, conn):
        revoke_assignment(
            side,
            actor=world.staff_a,
            assignment_id=world.assignment_now.id,
            clock=factory.clock,
            auditor=auditor_for(factory),
            attempted="test",
        )
        pending = pool.submit(
            mentor.post, f"/api/children/{world.child.id}/records", json=RECORD_BODY
        )
        wait_until_blocked(admin_engine, conn)  # FOR SHARE waits for the revoking UPDATE
        conn.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 403
    assert _new_records(factory, world) == 0
    revoked_at = factory.db.scalar(
        select(Assignment.revoked_at).where(Assignment.id == world.assignment_now.id)
    )
    assert revoked_at is not None
