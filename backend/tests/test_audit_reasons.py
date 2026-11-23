"""Denied mentor requests: one audit row each, with the reason the screen never shows."""

from __future__ import annotations

from typing import Any

import pytest
from app.models import AppUser, AuditLog
from sqlalchemy import select

from tests.factories import Factory
from tests.fixed_clock import FixedClock
from tests.scenario import END, PREV_END, PREV_START, START, World, build_world, kst

RECORDS_TEMPLATE = "/api/children/{child_id}/records"


@pytest.fixture
def world(factory: Factory) -> World:
    return build_world(factory)


def _denied_details(factory: Factory) -> list[dict[str, Any]]:
    rows = factory.db.scalars(
        select(AuditLog.detail).where(AuditLog.action == "access.denied").order_by(AuditLog.id)
    )
    return list(rows)


def _denied_once(factory: Factory, world: World, mentor: AppUser) -> dict[str, Any]:
    response = factory.client_for(mentor).get(f"/api/children/{world.child.id}/records")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    details = _denied_details(factory)
    assert len(details) == 1  # one request, one row
    assert details[0]["reason"] not in response.text  # the reason stays in the log
    assert details[0]["attempted"] == RECORDS_TEMPLATE  # route template, no real id
    return details[0]


def test_never_assigned_mentor_is_logged_as_not_assigned(factory: Factory, world: World) -> None:
    detail = _denied_once(factory, world, world.mentor_other)
    assert detail["reason"] == "not_assigned"
    assert "period" not in detail


def test_before_start_is_logged_with_the_period(
    factory: Factory, world: World, clock: FixedClock
) -> None:
    clock.set(kst(2026, 10, 5, 23, 59))
    detail = _denied_once(factory, world, world.mentor_now)
    assert detail["reason"] == "before_start"
    assert detail["period"] == f"{START.isoformat()}~{END.isoformat()}"


def test_after_end_is_logged_with_the_previous_period(factory: Factory, world: World) -> None:
    detail = _denied_once(factory, world, world.mentor_prev)
    assert detail["reason"] == "after_end"
    assert detail["period"] == f"{PREV_START.isoformat()}~{PREV_END.isoformat()}"


def test_revoked_is_logged_as_revoked(factory: Factory, world: World) -> None:
    staff = factory.client_for(world.staff_a)
    assert staff.post(f"/api/assignments/{world.assignment_now.id}/revoke").status_code == 200
    detail = _denied_once(factory, world, world.mentor_now)
    assert detail["reason"] == "revoked"
    assert detail["assignment_id"] == world.assignment_now.id
