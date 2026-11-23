"""Centers, user accounts, DB-backed sessions and one-time invite codes."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Role, timestamp_column


class Center(Base):
    """Isolation boundary: every query is scoped to the requester's center."""

    __tablename__ = "center"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = timestamp_column(nullable=False)


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        CheckConstraint("role IN ('director', 'staff', 'mentor')", name="role"),
        CheckConstraint("failed_count >= 0", name="failed_count"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    center_id: Mapped[int] = mapped_column(ForeignKey("center.id"), nullable=False, index=True)
    login_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(30), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    locked_until: Mapped[datetime | None] = timestamp_column(nullable=True)
    disabled_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False)

    center: Mapped[Center] = relationship(lazy="joined")

    @property
    def role_enum(self) -> Role:
        return Role(self.role)


class UserSession(Base):
    """Server-side session. Only an HMAC of the cookie token is stored."""

    __tablename__ = "user_session"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False)
    expires_at: Mapped[datetime] = timestamp_column(nullable=False)
    last_seen_at: Mapped[datetime] = timestamp_column(nullable=False)
    revoked_at: Mapped[datetime | None] = timestamp_column(nullable=True)


class Invite(Base):
    """One-time invite code (72 h). Only an HMAC of the code is stored."""

    __tablename__ = "invite"
    __table_args__ = (CheckConstraint("role IN ('staff', 'mentor', 'director')", name="role"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    center_id: Mapped[int] = mapped_column(ForeignKey("center.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    created_at: Mapped[datetime] = timestamp_column(nullable=False)
    expires_at: Mapped[datetime] = timestamp_column(nullable=False)
    used_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    used_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
