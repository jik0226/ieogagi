"""Child destruction racing writes that reference the child.

Global row lock order: record rows -> assignment rows -> child row. Each race
is run in both orders: the write in flight while destruction starts (it must
wait, then delete the new row too), and destruction in flight while the write
starts (the write must wait, then be refused with 403). Never a 500 and never
a row left pointing at the destroyed child. Deadlock cases: test_concurrency_lock_order.py.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from app.authz.policy import ChildAccess, authorize_child
from app.models import STAFF_ROLES, Role
from app.schemas.records import NoteCreateRequest, RecordCreateRequest
from app.services.notes import create_note
from app.services.records import create_record
from sqlalchemy.orm import Session

from tests.concurrency import (
    NOTHING_LEFT,
    SESSION_DAY,
    auditor_for,
    client_for,
    destroy_audits,
    held_session,
    left_for_child,
    start_destroy,
    wait_until_blocked,
)
from tests.factories import Factory
from tests.scenario import World, build_world


@pytest.fixture
def world(factory: Factory) -> World:
    return build_world(factory)


def _authorize(side: Session, factory: Factory, world: World, *, mentor: bool) -> ChildAccess:
    return authorize_child(
        side,
        user=world.mentor_now if mentor else world.staff_a,
        child_id=world.child.id,
        today=factory.clock.today_kst(),
        auditor=auditor_for(factory),
        allowed_roles=frozenset({Role.MENTOR}) if mentor else STAFF_ROLES,
        attempted="test",
        lock=True,
    )


def test_destroy_waits_for_an_in_flight_record_create(
    app_engine, admin_engine, factory: Factory, world: World
) -> None:
    director = client_for(factory, world.director_a)
    # The pool is entered first so it exits last (see test_external_review.py).
    with ThreadPoolExecutor(max_workers=1) as pool, held_session(app_engine) as (side, conn):
        access = _authorize(side, factory, world, mentor=True)
        payload = RecordCreateRequest(session_date=SESSION_DAY, did="새 기록")
        create_record(
            side, access=access, payload=payload, clock=factory.clock, auditor=auditor_for(factory)
        )
        pending = pool.submit(director.delete, f"/api/children/{world.child.id}")
        wait_until_blocked(admin_engine, conn)
        conn.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 204
    assert left_for_child(factory, world.child.id) == NOTHING_LEFT
    assert destroy_audits(factory)[0]["records"] == len(world.prior_records) + 1


def test_record_create_waits_for_destroy_then_is_refused(
    app_engine, admin_engine, factory: Factory, world: World
) -> None:
    mentor = client_for(factory, world.mentor_now)
    body = {"session_date": SESSION_DAY.isoformat(), "did": "새 기록"}
    with ThreadPoolExecutor(max_workers=1) as pool, held_session(app_engine) as (side, conn):
        start_destroy(side, factory, world)
        pending = pool.submit(mentor.post, f"/api/children/{world.child.id}/records", json=body)
        wait_until_blocked(admin_engine, conn)
        conn.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 403
    assert left_for_child(factory, world.child.id) == NOTHING_LEFT


def test_destroy_waits_for_an_in_flight_note_create(
    app_engine, admin_engine, factory: Factory, world: World
) -> None:
    director = client_for(factory, world.director_a)
    with ThreadPoolExecutor(max_workers=1) as pool, held_session(app_engine) as (side, conn):
        access = _authorize(side, factory, world, mentor=False)
        create_note(
            side,
            access=access,
            payload=NoteCreateRequest(share_text="공유 문구"),
            keyring=factory.secrets.keyring,
            clock=factory.clock,
            auditor=auditor_for(factory),
        )
        pending = pool.submit(director.delete, f"/api/children/{world.child.id}")
        wait_until_blocked(admin_engine, conn)
        conn.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 204
    assert left_for_child(factory, world.child.id) == NOTHING_LEFT
    assert destroy_audits(factory)[0]["notes"] == 1


@pytest.mark.parametrize("target", ["note", "assignment"])
def test_staff_insert_waits_for_destroy_then_is_refused(
    target: str, app_engine, admin_engine, factory: Factory, world: World
) -> None:
    """Staff inserts take no assignment lock; the shared child lock makes them wait."""
    staff = client_for(factory, world.staff_a)
    child_id = world.child.id
    if target == "note":
        url, body = f"/api/children/{child_id}/notes", {"share_text": "공유 문구"}
    else:
        url = "/api/assignments"
        body = {
            "mentor_id": world.mentor_other.id,
            "child_id": child_id,
            "start_date": "2026-10-20",
            "end_date": "2026-11-20",
        }
    with ThreadPoolExecutor(max_workers=1) as pool, held_session(app_engine) as (side, conn):
        start_destroy(side, factory, world)
        pending = pool.submit(staff.post, url, json=body)
        wait_until_blocked(admin_engine, conn)
        conn.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 403
    assert left_for_child(factory, child_id) == NOTHING_LEFT


def test_correction_and_hide_wait_for_destroy_then_are_refused(
    app_engine, admin_engine, factory: Factory, world: World
) -> None:
    own = factory.record(world.child, world.mentor_now, SESSION_DAY, did="원본")
    other = world.prior_records[0]
    mentor = client_for(factory, world.mentor_now)
    staff = client_for(factory, world.staff_a)
    correction = {"did": "정정본", "stuck": "", "next_step": ""}
    hide = {"reason_code": "SENSITIVE"}
    with ThreadPoolExecutor(max_workers=2) as pool, held_session(app_engine) as (side, conn):
        start_destroy(side, factory, world)
        corrected = pool.submit(mentor.post, f"/api/records/{own.id}/corrections", json=correction)
        # Different records: a second waiter on the same row would queue behind the first.
        hidden = pool.submit(staff.post, f"/api/records/{other.id}/hide", json=hide)
        wait_until_blocked(admin_engine, conn, count=2)
        conn.commit()
        responses = [corrected.result(timeout=10), hidden.result(timeout=10)]
    assert [response.status_code for response in responses] == [403, 403]
    assert left_for_child(factory, world.child.id) == NOTHING_LEFT
