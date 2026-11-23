"""Cross-cutting security properties: CSRF, error output, headers, crypto, grants."""

from __future__ import annotations

import pytest
from app.models import Role, StaffNote
from app.schemas.common import MAX_ID
from app.security.crypto import EncryptedNote, NoteDecryptionError, decrypt_note
from sqlalchemy import Engine, text
from sqlalchemy.exc import ProgrammingError

from tests.factories import Factory


def test_state_change_without_origin_is_rejected(factory: Factory, make_client) -> None:
    user = factory.user(factory.center(), Role.STAFF)
    client = make_client()
    no_origin = client.post(
        "/api/auth/login",
        json={"login_id": user.login_id, "password": factory.password},
        headers={"Origin": ""},
    )
    assert no_origin.status_code == 403
    evil = client.post(
        "/api/auth/login",
        json={"login_id": user.login_id, "password": factory.password},
        headers={"Origin": "https://evil.example"},
    )
    assert evil.status_code == 403


def test_security_headers_present(make_client) -> None:
    response = make_client().get("/api/health")
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in response.headers["content-security-policy"]


def test_validation_error_does_not_echo_input(make_client) -> None:
    secret_like = "<script>alert(1)</script>"
    response = make_client().post(
        "/api/auth/login", json={"login_id": secret_like, "password": "x", "extra": 1}
    )
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "VALIDATION_FAILED"
    assert secret_like not in response.text
    assert "body.extra" in body["fields"]


def test_unhandled_error_returns_generic_500(factory: Factory, make_client, app) -> None:
    def explode() -> None:
        raise RuntimeError("internal detail INTERNAL-MARKER-42 at /srv/app/config.py")

    app.router.add_api_route("/api/test-explode", explode, methods=["GET"])
    client = make_client(raise_server_exceptions=False)
    response = client.get("/api/test-explode")
    assert response.status_code == 500
    assert response.json() == {
        "error": {"code": "INTERNAL_ERROR", "message": response.json()["error"]["message"]}
    }
    assert "INTERNAL-MARKER-42" not in response.text and "Traceback" not in response.text


def test_unknown_route_and_huge_id_are_not_500(factory: Factory) -> None:
    client = factory.client_for(factory.user(factory.center(), Role.STAFF))
    assert client.get("/api/nope").status_code == 404
    assert client.get(f"/api/children/{MAX_ID + 1}/records").status_code == 422
    assert client.get("/api/children/-1/records").status_code == 422


def test_note_ciphertext_moved_to_other_row_fails(factory: Factory) -> None:
    center = factory.center()
    staff = factory.user(center, Role.STAFF)
    child = factory.child(center, staff)
    original = factory.note(child, staff, body="알레르기 정보")
    other = factory.note(child, staff, share_text="다른 메모")
    keyring = factory.secrets.keyring
    moved = EncryptedNote(original.ciphertext, original.nonce, original.key_id)
    assert decrypt_note(keyring, moved, note_id=original.id, child_id=child.id) == "알레르기 정보"
    with pytest.raises(NoteDecryptionError):
        decrypt_note(keyring, moved, note_id=other.id, child_id=child.id)
    stored = factory.db.get(StaffNote, original.id)
    assert "알레르기".encode() not in stored.ciphertext


def test_note_body_roundtrip_and_audited(factory: Factory) -> None:
    center = factory.center()
    staff = factory.user(center, Role.STAFF)
    child = factory.child(center, staff)
    client = factory.client_for(staff)
    created = client.post(
        f"/api/children/{child.id}/notes",
        json={"body": "약물 복용 중", "share_text": "간식 전 확인"},
    )
    assert created.status_code == 201 and created.json()["has_body"] is True
    detail = client.get(f"/api/notes/{created.json()['id']}").json()
    assert detail["body"] == "약물 복용 중"
    logs = client.get("/api/audit-logs", params={"action": "note.view"}).json()
    assert logs["total"] == 1


def test_app_role_cannot_modify_audit_log(app_engine: Engine, factory: Factory) -> None:
    factory.client_for(factory.user(factory.center(), Role.STAFF)).get("/api/auth/me")
    with app_engine.connect() as conn:
        conn.execute(
            text(
                "INSERT INTO audit_log (action, result, detail, created_at) "
                "VALUES ('test.insert', 'success', '{}', now())"
            )
        )
        conn.commit()
        for statement in ("UPDATE audit_log SET action = 'tampered'", "DELETE FROM audit_log"):
            with pytest.raises(ProgrammingError):
                conn.execute(text(statement))
            conn.rollback()
        with pytest.raises(ProgrammingError):
            conn.execute(text("DELETE FROM app_user"))
        conn.rollback()


def test_control_characters_in_free_text_are_422(factory: Factory) -> None:
    """NUL and other control characters are refused at validation (not a DB error)."""
    center = factory.center()
    staff = factory.user(center, Role.STAFF)
    child = factory.child(center, staff)
    client = factory.client_for(staff)
    for bad in ("a\u0000b", "a\u0007b"):
        response = client.post(f"/api/children/{child.id}/notes", json={"share_text": bad})
        assert response.status_code == 422
    ok = client.post(f"/api/children/{child.id}/notes", json={"share_text": "줄\n바꿈\t허용"})
    assert ok.status_code == 201
