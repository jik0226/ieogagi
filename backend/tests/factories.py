"""Test data builders. Inserts rows directly with the admin session."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from itertools import count

from app.auth.sessions import issue_session
from app.config import AppSecrets, Settings
from app.models import AppUser, Assignment, Center, Child, Record, Role, StaffNote
from app.security.crypto import encrypt_note
from app.security.passwords import hash_password
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.fixed_clock import FixedClock

# Generated per test run so no credential literal lives in the repository.
TEST_PASSWORD = secrets.token_urlsafe(12) + "aA1!"
# A different valid-looking password that never matches any account.
WRONG_PASSWORD = secrets.token_urlsafe(12) + "zZ9!"
_PASSWORD_HASH = hash_password(TEST_PASSWORD)
_ids = count(1)


@dataclass
class Factory:
    db: Session
    settings: Settings
    secrets: AppSecrets
    clock: FixedClock
    make_client: Callable[..., TestClient]
    password: str = field(default=TEST_PASSWORD)

    def center(self, name: str = "햇살지역아동센터") -> Center:
        center = Center(name=name, created_at=self.clock.now())
        self.db.add(center)
        self.db.commit()
        return center

    def user(self, center: Center, role: Role, *, name: str | None = None) -> AppUser:
        serial = next(_ids)
        user = AppUser(
            center_id=center.id,
            login_id=f"{role.value}_{serial}",
            display_name=name or f"{role.value}{serial}",
            role=role.value,
            password_hash=_PASSWORD_HASH,
            failed_count=0,
            created_at=self.clock.now(),
        )
        self.db.add(user)
        self.db.commit()
        return user

    def child(
        self, center: Center, creator: AppUser, *, alias: str = "별빛", sensitive_basis: bool = True
    ) -> Child:
        now = self.clock.now()
        child = Child(
            center_id=center.id,
            alias=alias,
            grade="중2",
            consent_at=now,
            sensitive_basis_at=now if sensitive_basis else None,
            created_by=creator.id,
            created_at=now,
        )
        self.db.add(child)
        self.db.commit()
        return child

    def assignment(
        self, mentor: AppUser, child: Child, start: date, end: date, creator: AppUser
    ) -> Assignment:
        assignment = Assignment(
            mentor_id=mentor.id,
            child_id=child.id,
            start_date=start,
            end_date=end,
            created_by=creator.id,
            created_at=self.clock.now(),
        )
        self.db.add(assignment)
        self.db.commit()
        return assignment

    def record(
        self,
        child: Child,
        author: AppUser,
        session_date: date,
        *,
        did: str = "수업",
        corrects: Record | None = None,
        hidden: bool = False,
    ) -> Record:
        record = Record(
            child_id=child.id,
            author_id=author.id,
            session_date=session_date,
            did=did,
            stuck="막힌 곳",
            next_step="다음",
            corrects_id=corrects.id if corrects else None,
            hidden_at=self.clock.now() if hidden else None,
            hidden_reason_code="OTHER" if hidden else None,
            created_at=self.clock.now(),
        )
        self.db.add(record)
        self.db.commit()
        return record

    def note(
        self,
        child: Child,
        author: AppUser,
        *,
        share_text: str | None = None,
        body: str | None = None,
    ) -> StaffNote:
        note = StaffNote(
            child_id=child.id,
            author_id=author.id,
            share_text=share_text,
            created_at=self.clock.now(),
        )
        self.db.add(note)
        self.db.flush()
        if body:
            encrypted = encrypt_note(self.secrets.keyring, body, note_id=note.id, child_id=child.id)
            note.ciphertext, note.nonce, note.key_id = (
                encrypted.ciphertext,
                encrypted.nonce,
                encrypted.key_id,
            )
        self.db.commit()
        return note

    def client_for(self, user: AppUser, *, raise_server_exceptions: bool = True) -> TestClient:
        """A client already holding a valid session cookie for ``user``.

        With ``raise_server_exceptions=False`` a server error comes back as a 500.
        """
        token = issue_session(
            self.db,
            user=user,
            settings=self.settings,
            key=self.secrets.session_key,
            clock=self.clock,
        )
        self.db.commit()
        client = self.make_client(raise_server_exceptions=raise_server_exceptions)
        client.cookies.set(self.settings.cookie_name, token)
        return client
