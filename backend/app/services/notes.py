"""Staff notes: encrypted body (staff only) and plain share text (for mentors)."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.writer import Auditor
from app.authz.policy import ChildAccess, authorize_child, deny
from app.clock import Clock
from app.errors import InternalError, SensitiveBasisRequired
from app.models import STAFF_ROLES, AppUser, Child, StaffNote
from app.schemas.records import AuthorOut, NoteCreateRequest, NoteDetailOut, NoteSummaryOut
from app.security.crypto import (
    EncryptedNote,
    NoteDecryptionError,
    NoteKeyring,
    decrypt_note,
    encrypt_note,
)

logger = logging.getLogger(__name__)
NOTE_LIST_LIMIT = 200


def _summary(note: StaffNote, author_name: str) -> NoteSummaryOut:
    return NoteSummaryOut(
        id=note.id,
        share_text=note.share_text,
        has_body=note.ciphertext is not None,
        author=AuthorOut(id=note.author_id, display_name=author_name),
        created_at=note.created_at,
    )


def create_note(
    db: Session,
    *,
    access: ChildAccess,
    payload: NoteCreateRequest,
    keyring: NoteKeyring,
    clock: Clock,
    auditor: Auditor,
) -> NoteSummaryOut:
    if payload.body:
        child = db.get(Child, access.child_id)
        if child is None or child.sensitive_basis_at is None:
            raise SensitiveBasisRequired
    note = StaffNote(
        child_id=access.child_id,
        author_id=access.user.id,
        share_text=payload.share_text or None,
        created_at=clock.now(),
    )
    db.add(note)
    db.flush()  # assigns note.id, which is bound into the AES-GCM associated data
    if payload.body:
        encrypted = encrypt_note(keyring, payload.body, note_id=note.id, child_id=access.child_id)
        note.ciphertext = encrypted.ciphertext
        note.nonce = encrypted.nonce
        note.key_id = encrypted.key_id
    auditor.stage(
        db,
        actor=access.user,
        action="note.create",
        target_type="note",
        target_id=note.id,
        detail={"child_id": access.child_id, "has_body": bool(payload.body)},
    )
    db.commit()
    return _summary(note, access.user.display_name)


def list_notes(db: Session, *, access: ChildAccess) -> list[NoteSummaryOut]:
    rows = db.execute(
        select(StaffNote, AppUser.display_name)
        .join(AppUser, AppUser.id == StaffNote.author_id)
        .where(StaffNote.child_id == access.child_id)
        .order_by(StaffNote.created_at.desc(), StaffNote.id.desc())
        .limit(NOTE_LIST_LIMIT)
    ).all()
    return [_summary(note, name) for note, name in rows]


def read_note(
    db: Session,
    *,
    user: AppUser,
    note_id: int,
    keyring: NoteKeyring,
    clock: Clock,
    auditor: Auditor,
    attempted: str,
) -> NoteDetailOut:
    row = db.execute(
        select(StaffNote, AppUser.display_name)
        .join(AppUser, AppUser.id == StaffNote.author_id)
        .join(Child, Child.id == StaffNote.child_id)
        .where(StaffNote.id == note_id, Child.center_id == user.center_id)
    ).one_or_none()
    if row is None:
        raise deny(
            auditor,
            db,
            user=user,
            attempted=attempted,
            target_type="note",
            target_id=note_id,
            detail={"reason": "other_center_or_missing"},
        )
    note, author_name = row
    authorize_child(
        db,
        user=user,
        child_id=note.child_id,
        today=clock.today_kst(),
        auditor=auditor,
        allowed_roles=STAFF_ROLES,
        attempted=attempted,
    )
    body: str | None = None
    if note.ciphertext is not None and note.nonce is not None and note.key_id is not None:
        try:
            body = decrypt_note(
                keyring,
                EncryptedNote(ciphertext=note.ciphertext, nonce=note.nonce, key_id=note.key_id),
                note_id=note.id,
                child_id=note.child_id,
            )
        except NoteDecryptionError as exc:
            logger.exception("note_decryption_failed", extra={"target_id": note.id})
            raise InternalError from exc
    auditor.stage(
        db,
        actor=user,
        action="note.view",
        target_type="note",
        target_id=note.id,
        detail={"child_id": note.child_id},
    )
    db.commit()
    return NoteDetailOut(**_summary(note, author_name).model_dump(), body=body)
