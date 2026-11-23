"""Handover card, record writing, correction, hide and redact."""

from __future__ import annotations

from datetime import date

import pytest
from app.models import AuditLog, Record
from sqlalchemy import select

from tests.factories import Factory
from tests.scenario import World, build_world


@pytest.fixture
def world(factory: Factory) -> World:
    return build_world(factory)


def test_handover_card_has_latest_four_before_start_and_share_texts(
    factory: Factory, world: World
) -> None:
    factory.note(world.child, world.staff_a, share_text="간식 제공 전 담당자 확인")
    factory.note(world.child, world.staff_a, body="원문은 카드에 나오면 안 됨")
    factory.record(world.child, world.mentor_now, date(2026, 10, 8), did="후임 기록")
    card = factory.client_for(world.mentor_now).get(f"/api/children/{world.child.id}/handover-card")
    assert card.status_code == 200
    data = card.json()
    assert [r["session_no"] for r in data["records"]] == [6, 5, 4, 3]
    assert data["records"][0]["session_date"] == "2026-10-05"
    assert data["share_texts"] == ["간식 제공 전 담당자 확인"]
    assert "원문은" not in card.text and "ciphertext" not in card.text
    assert data["assignment"] == {"start_date": "2026-10-06", "end_date": "2026-12-20"}


def test_mentor_writes_record_with_sensitive_confirmation(factory: Factory, world: World) -> None:
    client = factory.client_for(world.mentor_now)
    url = f"/api/children/{world.child.id}/records"
    body = {
        "session_date": "2026-10-20",
        "did": "분수 계산",
        "stuck": "병원 다녀와서 피곤",
        "next_step": "약분 연습",
    }
    first = client.post(url, json=body)
    assert first.status_code == 422
    assert first.json()["error"]["code"] == "SENSITIVE_CONFIRM_REQUIRED"
    assert first.json()["error"]["categories"] == ["health"]
    saved = client.post(url, json={**body, "sensitive_confirmed": True})
    assert saved.status_code == 201
    math_terms = {**body, "stuck": "약수와 약분 헷갈림", "session_date": "2026-10-19"}
    assert client.post(url, json=math_terms).status_code == 201
    prompts = factory.db.scalars(
        select(AuditLog).where(AuditLog.action == "record.sensitive_prompt")
    ).all()
    assert len(prompts) == 1


@pytest.mark.parametrize("session_date", ["2026-10-05", "2026-10-21"])
def test_record_date_must_be_in_period_and_not_future(
    factory: Factory, world: World, session_date: str
) -> None:
    client = factory.client_for(world.mentor_now)
    body = {"session_date": session_date, "did": "수업", "stuck": "", "next_step": ""}
    response = client.post(f"/api/children/{world.child.id}/records", json=body)
    assert response.status_code == 422


def test_empty_record_is_rejected(factory: Factory, world: World) -> None:
    client = factory.client_for(world.mentor_now)
    body = {"session_date": "2026-10-20", "did": "  ", "stuck": "", "next_step": ""}
    assert client.post(f"/api/children/{world.child.id}/records", json=body).status_code == 422


def test_correction_appends_and_cannot_fork(factory: Factory, world: World) -> None:
    original = factory.record(world.child, world.mentor_now, date(2026, 10, 13), did="원본")
    client = factory.client_for(world.mentor_now)
    body = {"did": "정정본", "stuck": "", "next_step": ""}
    first = client.post(f"/api/records/{original.id}/corrections", json=body)
    assert first.status_code == 201 and first.json()["corrects_id"] == original.id
    second = client.post(f"/api/records/{original.id}/corrections", json=body)
    assert second.status_code == 409
    chained = client.post(f"/api/records/{first.json()['id']}/corrections", json=body)
    assert chained.status_code == 201
    stored = factory.db.get(Record, original.id, populate_existing=True)
    assert stored is not None and stored.did == "원본"


def test_staff_hide_and_redact_keep_rows(factory: Factory, world: World) -> None:
    record = world.prior_records[0]
    client = factory.client_for(world.staff_a)
    hidden = client.post(f"/api/records/{record.id}/hide", json={"reason_code": "SENSITIVE"})
    assert hidden.status_code == 200 and hidden.json()["hidden_reason_code"] == "SENSITIVE"
    again = client.post(f"/api/records/{record.id}/hide", json={"reason_code": "OTHER"})
    assert again.status_code == 409
    redacted = client.post(f"/api/records/{record.id}/redact", json={"fields": ["stuck"]})
    assert redacted.status_code == 200
    assert redacted.json()["stuck"] == "" and redacted.json()["did"] == "1회 수업"
    bad = client.post(f"/api/records/{record.id}/redact", json={"fields": ["password"]})
    assert bad.status_code == 422
    staff_view = client.get(f"/api/children/{world.child.id}/records").json()
    assert len(staff_view) == len(world.prior_records)
    assert {"author", "hidden_at", "superseded"} <= set(staff_view[0])
    factory.record(world.child, world.mentor_now, date(2026, 10, 15), did="후임 기록")
    mentor_view = factory.client_for(world.mentor_now).get(
        f"/api/children/{world.child.id}/records"
    )
    assert mentor_view.status_code == 200
    assert len(mentor_view.json()) == 1
    assert "hidden_at" not in mentor_view.text and "author" not in mentor_view.text


def test_mentor_home_lists_active_and_upcoming(factory: Factory, world: World) -> None:
    upcoming_child = factory.child(world.center_a, world.staff_a, alias="새봄")
    factory.assignment(
        world.mentor_now, upcoming_child, date(2026, 11, 1), date(2026, 12, 31), world.staff_a
    )
    items = factory.client_for(world.mentor_now).get("/api/me/assignments").json()
    assert [(i["child"]["alias"], i["status"]) for i in items] == [
        ("별빛", "active"),
        ("새봄", "upcoming"),
    ]
    assert factory.client_for(world.mentor_prev).get("/api/me/assignments").json() == []


def test_common_health_words_prompt_and_staff_view_has_session_numbers(
    factory: Factory, world: World
) -> None:
    mentor = factory.client_for(world.mentor_now)
    body = {"session_date": "2026-10-20", "did": "감기 때문에 쉬었다", "stuck": "", "next_step": ""}
    response = mentor.post(f"/api/children/{world.child.id}/records", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["categories"] == ["health"]
    staff_view = factory.client_for(world.staff_a).get(f"/api/children/{world.child.id}/records")
    numbers = [r["session_no"] for r in staff_view.json()]
    assert numbers == [6, 5, 4, 3, 2, 1]
