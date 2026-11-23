"""Invites die with the issuer's authority: a disabled issuer's unused code is refused."""

from __future__ import annotations

import secrets
from datetime import timedelta

from app.config import AppSecrets
from app.models import AppUser, AuditLog, Invite, Role
from app.security.tokens import new_invite_code
from app.services.auth_service import invite_digest
from sqlalchemy import select

from tests.factories import Factory
from tests.fixed_clock import FixedClock

# Valid new-account password generated per run (no credential literal in the repo).
NEW_PASSWORD = secrets.token_urlsafe(12) + "Qq7!"


def _issue_invite(factory: Factory, issuer: AppUser, role: str) -> str:
    response = factory.client_for(issuer).post("/api/invites", json={"role": role})
    assert response.status_code == 201
    return response.json()["code"]


def _disable(factory: Factory, director: AppUser, target: AppUser) -> None:
    response = factory.client_for(director).post(f"/api/users/{target.id}/disable")
    assert response.status_code == 200


def _signup(client, code: str, login_id: str):
    body = {"code": code, "login_id": login_id, "display_name": "새멘토", "password": NEW_PASSWORD}
    return client.post("/api/auth/signup", json=body)


def _signup_audit(factory: Factory) -> list[AuditLog]:
    query = select(AuditLog).where(AuditLog.action == "auth.signup").order_by(AuditLog.id)
    return list(factory.db.scalars(query))


def test_disabled_issuers_invite_is_refused_like_a_bad_code(factory: Factory, make_client) -> None:
    center = factory.center()
    director = factory.user(center, Role.DIRECTOR)
    staff = factory.user(center, Role.STAFF)
    code = _issue_invite(factory, staff, "mentor")
    _disable(factory, director, staff)
    client = make_client()
    never_issued = new_invite_code()

    verify = client.post("/api/auth/invites/verify", json={"code": code})
    bad_verify = client.post("/api/auth/invites/verify", json={"code": never_issued})
    assert verify.status_code == bad_verify.status_code == 404
    assert verify.json() == bad_verify.json()

    signup = _signup(client, code, "late_mentor")
    bad_signup = _signup(client, never_issued, "late_mentor")
    assert signup.status_code == bad_signup.status_code == 404
    assert signup.json() == bad_signup.json()

    # Nothing was created or consumed: the code stays unused and no account exists.
    assert factory.db.scalar(select(Invite.used_at)) is None
    assert factory.db.scalar(select(AppUser).where(AppUser.login_id == "late_mentor")) is None

    # One row per request; only the log tells the two refusals apart.
    refused, bad = _signup_audit(factory)
    assert refused.detail == {"reason": "issuer_disabled"}
    assert refused.result == "denied" and refused.center_id == center.id
    assert refused.target_type == "invite" and refused.target_id is not None
    assert bad.detail == {"reason": "invalid_invite"} and bad.center_id is None
    assert "issuer_disabled" not in signup.text
    # The denied row lands in the center's own audit log, where staff can see it.
    page = factory.client_for(director).get("/api/audit-logs", params={"action": "auth.signup"})
    assert [item["detail"] for item in page.json()["items"]] == [{"reason": "issuer_disabled"}]


def test_active_colleagues_invite_still_signs_up(factory: Factory, make_client) -> None:
    center = factory.center()
    director = factory.user(center, Role.DIRECTOR)
    leaving, staying = factory.user(center, Role.STAFF), factory.user(center, Role.STAFF)
    _issue_invite(factory, leaving, "mentor")
    code = _issue_invite(factory, staying, "mentor")
    _disable(factory, director, leaving)
    client = make_client()
    assert client.post("/api/auth/invites/verify", json={"code": code}).status_code == 200
    signup = _signup(client, code, "kept_mentor")
    assert signup.status_code == 201 and signup.json()["role"] == "mentor"


def test_cli_director_invite_without_issuer_still_signs_up(
    factory: Factory, make_client, app_secrets: AppSecrets, clock: FixedClock
) -> None:
    # `add-center` issues the first director invite with no issuer (created_by NULL).
    center = factory.center()
    code = new_invite_code()
    factory.db.add(
        Invite(
            code_hash=invite_digest(app_secrets.session_key, code),
            center_id=center.id,
            role=Role.DIRECTOR.value,
            created_by=None,
            created_at=clock.now(),
            expires_at=clock.now() + timedelta(hours=72),
        )
    )
    factory.db.commit()
    signup = _signup(make_client(), code, "first_director")
    assert signup.status_code == 201 and signup.json()["role"] == "director"
