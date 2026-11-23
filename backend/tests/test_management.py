"""Director/staff management: children, assignments, accounts, destruction, audit."""

from __future__ import annotations

import pytest
from app.models import AuditLog, Child, Record, UserSession
from sqlalchemy import func, select

from tests.factories import Factory
from tests.scenario import World, build_world


@pytest.fixture
def world(factory: Factory) -> World:
    return build_world(factory)


def test_child_registration_requires_privacy_consent(factory: Factory, world: World) -> None:
    client = factory.client_for(world.staff_a)
    body = {"alias": "하늘", "grade": "초5", "privacy_consent_confirmed": False}
    refused = client.post("/api/children", json=body)
    assert refused.status_code == 422
    assert "동의" in refused.json()["error"]["message"]
    created = client.post("/api/children", json={**body, "privacy_consent_confirmed": True})
    assert created.status_code == 201 and created.json()["sensitive_basis_at"] is None
    child_id = created.json()["id"]
    confirmed = client.post(f"/api/children/{child_id}/sensitive-basis")
    assert confirmed.status_code == 200 and confirmed.json()["sensitive_basis_at"]
    assert client.post(f"/api/children/{child_id}/sensitive-basis").status_code == 409


def test_child_alias_and_grade_are_validated(factory: Factory, world: World) -> None:
    client = factory.client_for(world.staff_a)
    for alias, grade in (("<b>x</b>", "초5"), ("하늘", "대1"), ("가" * 21, "초1")):
        body = {"alias": alias, "grade": grade, "privacy_consent_confirmed": True}
        assert client.post("/api/children", json=body).status_code == 422


def test_assignment_rules(factory: Factory, world: World) -> None:
    client = factory.client_for(world.staff_a)
    base = {
        "mentor_id": world.mentor_other.id,
        "child_id": world.child.id,
        "start_date": "2026-11-01",
        "end_date": "2026-12-31",
    }
    assert client.post("/api/assignments", json=base).status_code == 201
    reversed_period = {**base, "start_date": "2027-01-01"}
    assert client.post("/api/assignments", json=reversed_period).status_code == 422
    too_long = {**base, "end_date": "2027-12-31"}
    assert client.post("/api/assignments", json=too_long).status_code == 422
    other_center_child = {**base, "child_id": world.child_b.id}
    assert client.post("/api/assignments", json=other_center_child).status_code == 403
    staff_as_mentor = {**base, "mentor_id": world.staff_a2.id}
    assert client.post("/api/assignments", json=staff_as_mentor).status_code == 403
    listed = client.get("/api/assignments", params={"child_id": world.child.id}).json()
    assert {a["status"] for a in listed} == {"upcoming", "active", "ended"}


def test_user_list_flags_mentors_whose_assignments_ended(factory: Factory, world: World) -> None:
    users = factory.client_for(world.staff_a).get("/api/users").json()
    flags = {u["id"]: u["assignment_ended"] for u in users}
    assert flags[world.mentor_prev.id] is True
    assert flags[world.mentor_now.id] is False
    assert flags[world.mentor_other.id] is False  # never assigned yet
    assert world.mentor_b.id not in flags


def test_disable_revokes_all_sessions(factory: Factory, world: World) -> None:
    factory.client_for(world.mentor_now)
    factory.client_for(world.mentor_now)
    response = factory.client_for(world.director_a).post(f"/api/users/{world.staff_a2.id}/disable")
    assert response.status_code == 200
    staff = factory.client_for(world.staff_a)
    assert staff.post(f"/api/users/{world.mentor_now.id}/disable").status_code == 200
    active = factory.db.scalar(
        select(func.count())
        .select_from(UserSession)
        .where(UserSession.user_id == world.mentor_now.id, UserSession.revoked_at.is_(None))
    )
    assert active == 0
    assert staff.post(f"/api/users/{world.mentor_now.id}/disable").status_code == 409
    assert staff.post(f"/api/users/{world.staff_a.id}/disable").status_code == 403


def test_director_destroys_child_and_audit_history_remains(factory: Factory, world: World) -> None:
    child_id = world.child.id
    director = factory.client_for(world.director_a)
    director.get(f"/api/children/{child_id}/records")
    assert director.delete(f"/api/children/{child_id}").status_code == 204
    assert factory.db.get(Child, child_id, populate_existing=True) is None
    remaining = factory.db.scalar(
        select(func.count()).select_from(Record).where(Record.child_id == child_id)
    )
    assert remaining == 0
    actions = set(factory.db.scalars(select(AuditLog.action)).all())
    assert {"record.view", "child.destroy"} <= actions
    logs = director.get("/api/audit-logs", params={"action": "child.destroy"}).json()
    assert logs["items"][0]["detail"]["records"] == len(world.prior_records)
    assert "별빛" not in str(logs)


def test_denials_are_audited_with_reason(factory: Factory, world: World) -> None:
    factory.client_for(world.mentor_prev).get(f"/api/children/{world.child.id}/records")
    page = (
        factory.client_for(world.staff_a)
        .get("/api/audit-logs", params={"action": "access.denied", "result": "denied"})
        .json()
    )
    assert page["total"] == 1
    detail = page["items"][0]["detail"]
    assert detail["reason"] == "after_end" and detail["period"] == "2026-06-01~2026-10-05"


def test_audit_log_paging_is_bounded(factory: Factory, world: World) -> None:
    client = factory.client_for(world.staff_a)
    assert client.get("/api/audit-logs", params={"limit": 101}).status_code == 422
    assert client.get("/api/audit-logs", params={"action": "x'; DROP"}).status_code == 422
