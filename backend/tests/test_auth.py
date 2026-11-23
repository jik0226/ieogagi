"""Login, lockout, invites, signup and session expiry."""

from __future__ import annotations

import secrets
from datetime import timedelta

from app.models import AppUser, AuditLog, Invite, Role
from app.security.ratelimit import limiter
from app.services import auth_service
from sqlalchemy import select, update

from tests.factories import WRONG_PASSWORD, Factory
from tests.fixed_clock import FixedClock

# Valid new-account password generated per run (no credential literal in the repo).
NEW_PASSWORD = secrets.token_urlsafe(12) + "Qq7!"


def _login(client, login_id: str, password: str):
    return client.post("/api/auth/login", json={"login_id": login_id, "password": password})


def _issue_invite(factory: Factory, issuer: AppUser, role: str) -> str:
    response = factory.client_for(issuer).post("/api/invites", json={"role": role})
    assert response.status_code == 201
    return response.json()["code"]


def test_login_sets_strict_session_cookie_and_me_works(factory: Factory, make_client) -> None:
    center = factory.center()
    user = factory.user(center, Role.STAFF)
    client = make_client()
    response = _login(client, user.login_id, factory.password)
    assert response.status_code == 200
    cookie = response.headers["set-cookie"].lower()
    for flag in ("httponly", "secure", "samesite=strict", "path=/"):
        assert flag in cookie
    # Diagnosis 02.10: Max-Age follows the server idle timeout (see test_session_cookie.py).
    assert f"max-age={factory.settings.session_idle_minutes * 60}" in cookie
    me = client.get("/api/auth/me").json()
    assert me["role"] == "staff" and me["center"]["name"] == center.name


def test_wrong_password_and_unknown_account_get_same_message(factory: Factory, make_client) -> None:
    user = factory.user(factory.center(), Role.MENTOR)
    client = make_client()
    wrong = _login(client, user.login_id, WRONG_PASSWORD)
    unknown = _login(client, "nobody_here", WRONG_PASSWORD)
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_five_failures_lock_account_for_15_minutes(
    factory: Factory, make_client, clock: FixedClock
) -> None:
    user = factory.user(factory.center(), Role.MENTOR)
    client = make_client()
    for _ in range(5):
        assert _login(client, user.login_id, WRONG_PASSWORD).status_code == 401
    locked = _login(client, user.login_id, factory.password)
    assert locked.status_code == 401
    assert locked.json() == _login(client, user.login_id, WRONG_PASSWORD).json()
    clock.set(clock.now() + timedelta(minutes=16))
    assert _login(client, user.login_id, factory.password).status_code == 200
    reasons = factory.db.scalars(select(AuditLog.detail).where(AuditLog.action == "auth.login"))
    assert any(detail.get("reason") == "locked" for detail in reasons)


def test_login_rate_limit_per_ip(factory: Factory, make_client, app) -> None:
    limiter.enabled = True
    try:
        client = make_client()
        statuses = [_login(client, "nobody_here", WRONG_PASSWORD).status_code for _ in range(11)]
    finally:
        limiter.enabled = False
    assert statuses[:10] == [401] * 10
    assert statuses[10] == 429


def test_invite_signup_is_single_use(factory: Factory, make_client) -> None:
    center = factory.center()
    director = factory.user(center, Role.DIRECTOR)
    code = _issue_invite(factory, director, "staff")
    client = make_client()
    verify = client.post("/api/auth/invites/verify", json={"code": code})
    assert verify.status_code == 200 and verify.json()["role"] == "staff"
    body = {
        "code": code,
        "login_id": "new_staff",
        "display_name": "김담당",
        "password": NEW_PASSWORD,
    }
    assert client.post("/api/auth/signup", json=body).status_code == 201
    again = client.post("/api/auth/signup", json={**body, "login_id": "other_staff"})
    assert again.status_code == 404
    assert client.post("/api/auth/invites/verify", json={"code": code}).status_code == 404
    stored = factory.db.scalar(select(Invite))
    assert stored is not None and code not in stored.code_hash


def test_signup_duplicate_login_id_keeps_invite_usable(factory: Factory, make_client) -> None:
    center = factory.center()
    staff = factory.user(center, Role.STAFF)
    code = _issue_invite(factory, staff, "mentor")
    client = make_client()
    body = {
        "code": code,
        "login_id": staff.login_id,
        "display_name": "멘토",
        "password": NEW_PASSWORD,
    }
    assert client.post("/api/auth/signup", json=body).status_code == 409
    retry = client.post("/api/auth/signup", json={**body, "login_id": "fresh_mentor"})
    assert retry.status_code == 201 and retry.json()["role"] == "mentor"


def test_expired_invite_is_rejected(factory: Factory, make_client, clock: FixedClock) -> None:
    staff = factory.user(factory.center(), Role.STAFF)
    code = _issue_invite(factory, staff, "mentor")
    clock.set(clock.now() + timedelta(hours=72, seconds=1))
    response = make_client().post("/api/auth/invites/verify", json={"code": code})
    assert response.status_code == 404


def test_weak_password_is_rejected(factory: Factory, make_client) -> None:
    staff = factory.user(factory.center(), Role.STAFF)
    code = _issue_invite(factory, staff, "mentor")
    for weak in ("short1A!", "alllowercaseletters"):
        body = {"code": code, "login_id": "weak_user", "display_name": "약한", "password": weak}
        response = make_client().post("/api/auth/signup", json=body)
        assert response.status_code == 422
        assert weak not in response.text


def test_control_characters_in_password_are_422_and_not_echoed(
    factory: Factory, make_client
) -> None:
    center = factory.center()
    user = factory.user(center, Role.MENTOR)
    code = _issue_invite(factory, factory.user(center, Role.STAFF), "mentor")
    client = make_client()
    marker = secrets.token_hex(8)
    for bad in (f"{marker}\x00{NEW_PASSWORD}", f"{NEW_PASSWORD}\x07{marker}"):
        signup = {"code": code, "login_id": "ctrl_user", "display_name": "제어", "password": bad}
        responses = [
            _login(client, user.login_id, bad),
            client.post("/api/auth/signup", json=signup),
        ]
        for response in responses:
            assert response.status_code == 422
            assert marker not in response.text and NEW_PASSWORD not in response.text
    # Refused before any account work: no login attempt counted, the invite unused.
    assert factory.db.scalar(select(AuditLog.id).where(AuditLog.action == "auth.login")) is None
    assert client.post("/api/auth/invites/verify", json={"code": code}).status_code == 200


def test_account_disabled_during_login_is_logged_as_disabled(
    factory: Factory, make_client, admin_engine, monkeypatch
) -> None:
    """The refusal reason comes from the row after the claim, not the earlier load."""
    user = factory.user(factory.center(), Role.MENTOR)
    real_reserve = auth_service._reserve_attempt

    def disable_then_reserve(db, **kwargs) -> bool:
        with admin_engine.begin() as conn:
            disable = update(AppUser).where(AppUser.id == user.id)
            conn.execute(disable.values(disabled_at=factory.clock.now()))
        return real_reserve(db, **kwargs)

    monkeypatch.setattr(auth_service, "_reserve_attempt", disable_then_reserve)
    assert _login(make_client(), user.login_id, factory.password).status_code == 401
    details = factory.db.scalars(select(AuditLog.detail).where(AuditLog.action == "auth.login"))
    assert list(details) == [{"reason": "disabled"}]


def test_session_idle_timeout_and_logout(factory: Factory, clock: FixedClock) -> None:
    user = factory.user(factory.center(), Role.STAFF)
    client = factory.client_for(user)
    clock.set(clock.now() + timedelta(minutes=9))
    assert client.get("/api/auth/me").status_code == 200
    clock.set(clock.now() + timedelta(minutes=11))
    assert client.get("/api/auth/me").status_code == 401
    fresh = factory.client_for(user)
    assert fresh.post("/api/auth/logout").status_code == 204
    assert fresh.get("/api/auth/me").status_code == 401


def test_absolute_session_expiry(factory: Factory, clock: FixedClock) -> None:
    user = factory.user(factory.center(), Role.STAFF)
    client = factory.client_for(user)
    for _ in range(50):  # keep the session busy every 9 minutes for 7.5 hours
        clock.set(clock.now() + timedelta(minutes=9))
        assert client.get("/api/auth/me").status_code == 200
    clock.set(clock.now() + timedelta(minutes=35))
    assert client.get("/api/auth/me").status_code == 401
