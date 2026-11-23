"""Regression tests for the 2026-10-11 independent security review findings."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pytest
from app.db import build_session_factory
from app.models import AuditLog, UserSession
from app.schemas.records import MentorRecordOut
from pydantic import TypeAdapter
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import ProgrammingError

from tests.conftest import TEST_DB_URL
from tests.factories import WRONG_PASSWORD, Factory
from tests.scenario import World, build_world


@pytest.fixture
def world(factory: Factory) -> World:
    return build_world(factory)


def _login_body(login_id: str, password: str) -> dict[str, str]:
    return {"login_id": login_id, "password": password}


def test_denials_use_the_request_connection_only(app, factory: Factory, world: World) -> None:
    """Finding 1: a denied request must not need a second pooled connection."""
    engine = create_engine(TEST_DB_URL, pool_size=1, max_overflow=0, pool_timeout=2)

    @event.listens_for(engine, "connect")
    def _set_role(dbapi_connection, _record) -> None:
        with dbapi_connection.cursor() as cursor:
            cursor.execute("SET ROLE ieogagi_app")
        dbapi_connection.commit()

    app.state.session_factory = build_session_factory(engine)
    try:
        mentor = factory.client_for(world.mentor_other)
        started = time.monotonic()
        denied = mentor.get(f"/api/children/{world.child.id}/records")
        unknown = factory.make_client().post(
            "/api/auth/login", json=_login_body("nobody_here", WRONG_PASSWORD)
        )
        elapsed = time.monotonic() - started
    finally:
        engine.dispose()
    assert denied.status_code == 403
    assert unknown.status_code == 401
    assert elapsed < 2


def test_concurrent_wrong_passwords_cannot_pass_the_lock(factory: Factory, world: World) -> None:
    """Finding 2: at most 5 password checks, even when requests race."""
    login_id = world.mentor_now.login_id
    clients = [factory.make_client() for _ in range(12)]

    def attempt(client) -> int:
        return client.post(
            "/api/auth/login", json=_login_body(login_id, WRONG_PASSWORD)
        ).status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        statuses = list(pool.map(attempt, clients))
    assert statuses == [401] * 12
    details = factory.db.scalars(select(AuditLog.detail).where(AuditLog.action == "auth.login"))
    reasons = [detail["reason"] for detail in details]
    assert reasons.count("bad_password") <= 5
    assert reasons.count("locked") >= 7


def test_overlapping_assignment_rejected_so_revoke_closes_access(
    factory: Factory, world: World
) -> None:
    """Finding 3: a duplicate live assignment cannot keep access open after revoke."""
    staff = factory.client_for(world.staff_a)
    duplicate = {
        "mentor_id": world.mentor_now.id,
        "child_id": world.child.id,
        "start_date": "2026-10-10",
        "end_date": "2026-11-10",
    }
    assert staff.post("/api/assignments", json=duplicate).status_code == 409
    assert staff.post(f"/api/assignments/{world.assignment_now.id}/revoke").status_code == 200
    mentor = factory.client_for(world.mentor_now)
    assert mentor.get(f"/api/children/{world.child.id}/records").status_code == 403


def test_mentor_schema_strips_staff_fields(factory: Factory, world: World) -> None:
    """Finding 4: serializing through the mentor schema drops staff-only fields."""
    staff_view = factory.client_for(world.staff_a).get(f"/api/children/{world.child.id}/records")
    staff_item = staff_view.json()[0]
    dumped = TypeAdapter(list[MentorRecordOut]).dump_python(
        TypeAdapter(list[MentorRecordOut]).validate_python([staff_item]), mode="json"
    )
    assert set(dumped[0]) == set(MentorRecordOut.model_fields)


def test_out_of_range_dates_are_422(factory: Factory, world: World) -> None:
    """Finding 5: no date overflow reaches the database layer."""
    staff = factory.client_for(world.staff_a)
    assert staff.get("/api/audit-logs", params={"date_to": "9999-12-31"}).status_code == 422
    mentor = factory.client_for(world.mentor_now)
    body = {"session_date": "1900-01-01", "did": "x", "stuck": "", "next_step": ""}
    assert mentor.post(f"/api/children/{world.child.id}/records", json=body).status_code == 422


def test_unknown_keys_are_not_echoed(make_client) -> None:
    """Finding 6: client-chosen key names never come back in the error body."""
    payload = {"<img src=x onerror=alert(1)>": 1, "login_id": "abcd", "password": "x"}
    response = make_client().post("/api/auth/login", json=payload)
    assert response.status_code == 422
    assert "onerror" not in response.text
    assert response.json()["error"]["fields"] == ["body"]


def test_hidden_correction_restores_original(factory: Factory, world: World) -> None:
    """Finding 7: hiding a correction makes the original visible and correctable again."""
    original = factory.record(world.child, world.mentor_now, date(2026, 10, 13), did="원본")
    mentor = factory.client_for(world.mentor_now)
    body = {"did": "정정본", "stuck": "", "next_step": ""}
    correction = mentor.post(f"/api/records/{original.id}/corrections", json=body).json()
    staff = factory.client_for(world.staff_a)
    hide = staff.post(f"/api/records/{correction['id']}/hide", json={"reason_code": "SENSITIVE"})
    assert hide.status_code == 200
    visible = mentor.get(f"/api/children/{world.child.id}/records").json()
    assert [r["id"] for r in visible] == [original.id]
    again = mentor.post(f"/api/records/{original.id}/corrections", json=body)
    assert again.status_code == 201


def test_destroying_child_keeps_assignment_ended_signal(factory: Factory, world: World) -> None:
    """Finding 8: destruction detaches assignments instead of erasing the history."""
    director = factory.client_for(world.director_a)
    assert director.delete(f"/api/children/{world.child.id}").status_code == 204
    users = factory.client_for(world.staff_a).get("/api/users").json()
    flags = {u["id"]: u["assignment_ended"] for u in users}
    assert flags[world.mentor_prev.id] is True
    assert flags[world.mentor_now.id] is True  # its only assignment was revoked by destruction


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE app_user SET role = 'director'",
        "UPDATE app_user SET center_id = 2",
        "UPDATE record SET author_id = 1",
        "UPDATE assignment SET end_date = '2099-12-31'",
        "UPDATE child SET center_id = 2",
        "DELETE FROM assignment",
    ],
)
def test_app_role_cannot_update_identity_columns(app_engine, factory, statement: str) -> None:
    """Finding 10: column-level grants keep ownership and identity immutable."""
    with app_engine.connect() as conn:
        with pytest.raises(ProgrammingError):
            conn.execute(text(statement))
        conn.rollback()


def test_oversized_body_is_413(make_client) -> None:
    """Finding 11: large bodies are refused before parsing."""
    big = {"login_id": "abcd", "password": "x" * (70 * 1024)}
    response = make_client().post("/api/auth/login", json=big)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_logout_always_clears_cookie_and_login_revokes_old_token(
    factory: Factory, world: World, clock
) -> None:
    """Finding 12: expired sessions can log out; a new login drops the old token."""
    client = factory.client_for(world.staff_a)
    response = client.post(
        "/api/auth/login", json=_login_body(world.staff_a.login_id, factory.password)
    )
    assert response.status_code == 200
    sessions = factory.db.scalars(
        select(UserSession).where(UserSession.user_id == world.staff_a.id)
    ).all()
    assert sum(1 for s in sessions if s.revoked_at is None) == 1
    stale = factory.client_for(world.staff_a)
    clock.set(clock.now() + timedelta(hours=1))
    logout = stale.post("/api/auth/logout")
    assert logout.status_code == 204
    assert "max-age=0" in logout.headers["set-cookie"].lower()


def test_oversized_chunked_body_is_413(make_client) -> None:
    """Bodies without Content-Length are counted while streaming."""

    def chunks():
        yield b'{"login_id": "abcd", "password": "'
        for _ in range(80):
            yield b"x" * 1024
        yield b'"}'

    response = make_client().post(
        "/api/auth/login", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413
