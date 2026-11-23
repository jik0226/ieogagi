"""Lock order of child destruction against corrections (no deadlock, no 500).

Corrections lock their record first and the assignment second, so destruction
locks records -> assignments -> child. A record committed while destruction
waited for the assignment locks is retried rather than waited for.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pytest
from app.models import Assignment, AuditLog, Record
from app.services import children
from sqlalchemy import insert, select

from tests.concurrency import (
    NOTHING_LEFT,
    SESSION_DAY,
    client_for,
    destroy_audits,
    held_connection,
    held_session,
    left_for_child,
    record_row,
    start_destroy,
    wait_until_blocked,
)
from tests.factories import Factory
from tests.scenario import World, build_world


@pytest.fixture
def world(factory: Factory) -> World:
    return build_world(factory)


def test_destroy_and_an_in_flight_correction_do_not_deadlock(
    app_engine, admin_engine, factory: Factory, world: World
) -> None:
    """The correction holds its record and then asks for the assignment: destroy must
    not be holding the assignment while it waits for that record."""
    original = factory.record(world.child, world.mentor_now, SESSION_DAY, did="원본")
    director = client_for(factory, world.director_a)
    assignment = select(Assignment.id).where(Assignment.id == world.assignment_now.id)
    with ThreadPoolExecutor(max_workers=1) as pool, held_connection(app_engine) as conn:
        conn.execute(select(Record.id).where(Record.id == original.id).with_for_update())
        pending = pool.submit(director.delete, f"/api/children/{world.child.id}")
        wait_until_blocked(admin_engine, conn)
        conn.execute(assignment.with_for_update(read=True))  # deadlocks if destroy holds it
        conn.execute(
            insert(Record).values(
                **record_row(factory, world, corrects_id=original.id, did="정정본")
            )
        )
        conn.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 204
    assert left_for_child(factory, world.child.id) == NOTHING_LEFT


def test_destroy_retries_instead_of_deadlocking_on_a_late_record(
    app_engine, admin_engine, factory: Factory, world: World
) -> None:
    """A record committed while destroy waits for the assignment lock is not in its
    first record pass; a correction of it must not deadlock with destroy."""
    director = client_for(factory, world.director_a)
    assignment = select(Assignment.id).where(Assignment.id == world.assignment_now.id)
    late = record_row(factory, world, corrects_id=None, did="늦은 기록")
    with (
        ThreadPoolExecutor(max_workers=1) as pool,
        held_connection(app_engine) as creator,
        held_connection(app_engine) as other_writer,
        held_connection(app_engine) as corrector,
    ):
        creator.execute(assignment.with_for_update(read=True))
        late_id = creator.scalar(insert(Record).values(**late).returning(Record.id))
        other_writer.execute(assignment.with_for_update(read=True))
        pending = pool.submit(director.delete, f"/api/children/{world.child.id}")
        wait_until_blocked(admin_engine, creator)
        creator.commit()  # the late record is visible; destroy still waits for other_writer
        corrector.execute(select(Record.id).where(Record.id == late_id).with_for_update())
        other_writer.commit()  # destroy gets the assignment, finds the late record held
        wait_until_blocked(admin_engine, corrector)
        corrector.execute(assignment.with_for_update(read=True))  # deadlocks without the retry
        corrector.execute(
            insert(Record).values(**record_row(factory, world, corrects_id=late_id, did="정정본"))
        )
        corrector.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 204
    assert left_for_child(factory, world.child.id) == NOTHING_LEFT
    assert destroy_audits(factory)[0]["records"] == len(world.prior_records) + 2


def test_second_destroy_waits_then_is_refused(
    app_engine, admin_engine, factory: Factory, world: World
) -> None:
    """A destroy that waited for another one finds no child: 403, not a second success."""
    director = client_for(factory, world.director_a)
    with ThreadPoolExecutor(max_workers=1) as pool, held_session(app_engine) as (side, conn):
        start_destroy(side, factory, world)
        pending = pool.submit(director.delete, f"/api/children/{world.child.id}")
        wait_until_blocked(admin_engine, conn)
        conn.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 403
    assert len(destroy_audits(factory)) == 1
    denied = factory.db.scalar(select(AuditLog.detail).where(AuditLog.action == "access.denied"))
    assert denied is not None and denied["reason"] == "other_center_or_missing"


def test_destroy_gives_up_with_409_when_records_stay_held(
    factory: Factory, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If every attempt finds a record held by someone else, nothing is deleted."""
    monkeypatch.setattr(children, "_all_records_locked", lambda _db, _child_id: False)
    director = client_for(factory, world.director_a)
    response = director.delete(f"/api/children/{world.child.id}")
    assert response.status_code == 409
    left = left_for_child(factory, world.child.id)
    assert left["child"] == 1 and left["record"] == len(world.prior_records)
    assert destroy_audits(factory) == []
