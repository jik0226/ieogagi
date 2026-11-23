"""The 14 authorization boundary cases from the development plan (❷ 4절).

Each test name starts with its row number in the plan's table.
"""

from __future__ import annotations

from datetime import date

import pytest

from tests.factories import Factory
from tests.fixed_clock import FixedClock
from tests.scenario import END, START, World, build_world, kst


@pytest.fixture
def world(factory: Factory) -> World:
    return build_world(factory)


def _records_url(child_id: int) -> str:
    return f"/api/children/{child_id}/records"


def test_01_other_mentors_child_is_forbidden(factory: Factory, world: World) -> None:
    client = factory.client_for(world.mentor_other)
    assert client.get(_records_url(world.child.id)).status_code == 403
    assert client.get(f"/api/children/{world.child.id}/handover-card").status_code == 403


def test_02_day_before_start_is_forbidden(
    factory: Factory, world: World, clock: FixedClock
) -> None:
    clock.set(kst(2026, 10, 5, 23, 59))
    client = factory.client_for(world.mentor_now)
    assert client.get(_records_url(world.child.id)).status_code == 403


@pytest.mark.parametrize("day", [START, END])
def test_03_start_and_end_day_are_allowed(
    factory: Factory, world: World, clock: FixedClock, day: date
) -> None:
    clock.set(kst(day.year, day.month, day.day, 0, 0))
    client = factory.client_for(world.mentor_now)
    assert client.get(_records_url(world.child.id)).status_code == 200
    assert client.get(f"/api/children/{world.child.id}/handover-card").status_code == 200


def test_04_day_after_end_0030_kst_is_forbidden(
    factory: Factory, world: World, clock: FixedClock
) -> None:
    # 2026-12-21 00:30 KST is still 12-20 in UTC: the app must use the Korea date.
    clock.set(kst(2026, 12, 21, 0, 30))
    client = factory.client_for(world.mentor_now)
    assert client.get(_records_url(world.child.id)).status_code == 403


def test_05_next_request_after_revoke_is_forbidden(factory: Factory, world: World) -> None:
    mentor = factory.client_for(world.mentor_now)
    staff = factory.client_for(world.staff_a)
    assert mentor.get(_records_url(world.child.id)).status_code == 200
    revoked = staff.post(f"/api/assignments/{world.assignment_now.id}/revoke")
    assert revoked.status_code == 200
    assert mentor.get(_records_url(world.child.id)).status_code == 403


def test_06_existing_session_after_disable_is_401(factory: Factory, world: World) -> None:
    mentor = factory.client_for(world.mentor_now)
    staff = factory.client_for(world.staff_a)
    assert staff.post(f"/api/users/{world.mentor_now.id}/disable").status_code == 200
    response = mentor.get(_records_url(world.child.id))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_07_other_center_is_forbidden(factory: Factory, world: World) -> None:
    mentor_b = factory.client_for(world.mentor_b)
    staff_b = factory.client_for(world.staff_b)
    assert mentor_b.get(_records_url(world.child.id)).status_code == 403
    assert staff_b.get(_records_url(world.child.id)).status_code == 403
    assert staff_b.get(f"/api/children/{world.child.id}/notes").status_code == 403
    record_id = world.prior_records[0].id
    hide = staff_b.post(f"/api/records/{record_id}/hide", json={"reason_code": "OTHER"})
    assert hide.status_code == 403
    # Audit search is always scoped to the requester's own center.
    staff_a = factory.client_for(world.staff_a)
    staff_a.get(_records_url(world.child.id))
    logs = staff_b.get("/api/audit-logs").json()["items"]
    assert all(log["actor_id"] in {world.staff_b.id, world.mentor_b.id} for log in logs)


def test_08_correcting_other_mentor_or_child_record_is_forbidden(
    factory: Factory, world: World
) -> None:
    client = factory.client_for(world.mentor_now)
    other_mentors_record = world.prior_records[-1]
    body = {"did": "정정", "stuck": "", "next_step": ""}
    response = client.post(f"/api/records/{other_mentors_record.id}/corrections", json=body)
    assert response.status_code == 403
    child_b_record = factory.record(world.child_b, world.mentor_b, date(2026, 10, 10))
    response = client.post(f"/api/records/{child_b_record.id}/corrections", json=body)
    assert response.status_code == 403


def test_09_writing_outside_period_is_forbidden(
    factory: Factory, world: World, clock: FixedClock
) -> None:
    clock.set(kst(2026, 12, 21, 9, 0))
    client = factory.client_for(world.mentor_now)
    body = {"session_date": "2026-12-20", "did": "늦은 기록", "stuck": "", "next_step": ""}
    assert client.post(_records_url(world.child.id), json=body).status_code == 403


def test_10_hidden_and_superseded_records_are_excluded_for_mentor(
    factory: Factory, world: World
) -> None:
    hidden = factory.record(world.child, world.mentor_now, date(2026, 10, 7), hidden=True)
    original = factory.record(world.child, world.mentor_now, date(2026, 10, 14), did="원본")
    corrected = factory.record(
        world.child, world.mentor_now, date(2026, 10, 14), did="정정본", corrects=original
    )
    hidden_prior = world.prior_records[-1]
    factory.db.execute(
        hidden_prior.__table__.update()
        .where(hidden_prior.__table__.c.id == hidden_prior.id)
        .values(hidden_at=factory.clock.now(), hidden_reason_code="OTHER")
    )
    factory.db.commit()
    client = factory.client_for(world.mentor_now)
    ids = {r["id"] for r in client.get(_records_url(world.child.id)).json()}
    assert ids == {corrected.id}
    assert hidden.id not in ids
    card = client.get(f"/api/children/{world.child.id}/handover-card").json()
    card_dates = [r["session_date"] for r in card["records"]]
    assert "2026-10-05" not in card_dates
    assert len(card["records"]) == 4


def test_11_mentor_cannot_call_note_body_or_audit_api(factory: Factory, world: World) -> None:
    note = factory.note(world.child, world.staff_a, share_text="간식 전 확인", body="원문")
    client = factory.client_for(world.mentor_now)
    assert client.get(f"/api/notes/{note.id}").status_code == 403
    assert client.get(f"/api/children/{world.child.id}/notes").status_code == 403
    assert client.get("/api/audit-logs").status_code == 403


def test_12_staff_cannot_issue_staff_invite_or_destroy(factory: Factory, world: World) -> None:
    client = factory.client_for(world.staff_a)
    assert client.post("/api/invites", json={"role": "staff"}).status_code == 403
    assert client.delete(f"/api/children/{world.child.id}").status_code == 403


def test_13_staff_cannot_disable_director_or_other_staff(factory: Factory, world: World) -> None:
    client = factory.client_for(world.staff_a)
    assert client.post(f"/api/users/{world.director_a.id}/disable").status_code == 403
    assert client.post(f"/api/users/{world.staff_a2.id}/disable").status_code == 403


def test_14_note_body_requires_sensitive_basis(factory: Factory, world: World) -> None:
    child = factory.child(world.center_a, world.staff_a, alias="새싹", sensitive_basis=False)
    client = factory.client_for(world.staff_a)
    response = client.post(f"/api/children/{child.id}/notes", json={"body": "건강 관련 원문"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SENSITIVE_BASIS_REQUIRED"
    ok = client.post(f"/api/children/{child.id}/notes", json={"share_text": "공유 문구만"})
    assert ok.status_code == 201
