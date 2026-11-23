"""Session records (append-only) and encrypted staff notes."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    LargeBinary,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, timestamp_column

RECORD_FIELD_MAX = 500
NOTE_BODY_MAX = 2000
SHARE_TEXT_MAX = 200


class Record(Base):
    """A mentor's 3-field session record.

    Records are never overwritten. A correction is a new row whose
    ``corrects_id`` points at the corrected row; a partial unique index on
    ``corrects_id`` (visible rows only) makes concurrent double corrections
    impossible, while a correction that staff hid no longer blocks the chain.
    Staff may hide a row (with a reason code) or blank sensitive fields
    (``redacted_at``) but the row itself stays for accountability.
    """

    __tablename__ = "record"
    __table_args__ = (
        CheckConstraint(
            "hidden_reason_code IS NULL OR hidden_reason_code IN "
            "('INAPPROPRIATE', 'WRONG_CHILD', 'DUPLICATE', 'SENSITIVE', 'OTHER')",
            name="hidden_reason",
        ),
        Index("ix_record_child_session", "child_id", "session_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False, index=True)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    did: Mapped[str] = mapped_column(String(RECORD_FIELD_MAX), nullable=False, default="")
    stuck: Mapped[str] = mapped_column(String(RECORD_FIELD_MAX), nullable=False, default="")
    next_step: Mapped[str] = mapped_column(String(RECORD_FIELD_MAX), nullable=False, default="")
    corrects_id: Mapped[int | None] = mapped_column(ForeignKey("record.id"), nullable=True)
    hidden_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    hidden_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    hidden_reason_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    redacted_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    redacted_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False)


# Only one visible correction per record; hidden corrections do not count.
Index(
    "uq_record_corrects_id_visible",
    Record.corrects_id,
    unique=True,
    postgresql_where=Record.hidden_at.is_(None),
)


class StaffNote(Base):
    """Staff-only note. The body is AES-256-GCM ciphertext; share_text is plain.

    Mentors only ever receive ``share_text`` (through the handover card); no
    mentor-facing schema contains the ciphertext or the decrypted body.
    """

    __tablename__ = "staff_note"
    __table_args__ = (
        CheckConstraint(
            "(ciphertext IS NULL AND nonce IS NULL AND key_id IS NULL) OR "
            "(ciphertext IS NOT NULL AND nonce IS NOT NULL AND key_id IS NOT NULL)",
            name="cipher_fields",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    child_id: Mapped[int] = mapped_column(ForeignKey("child.id"), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    key_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    share_text: Mapped[str | None] = mapped_column(String(SHARE_TEXT_MAX), nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False)
