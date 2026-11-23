"""Children (alias + grade only) and mentor assignments.

``assignment`` is the single source of a mentor's access rights: a mentor can
read or write a child's data only while ``start_date <= today <= end_date``
and ``revoked_at IS NULL`` for one of their own assignments.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Index, String, func, literal
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, timestamp_column


class Child(Base):
    __tablename__ = "child"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    center_id: Mapped[int] = mapped_column(ForeignKey("center.id"), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(20), nullable=False)
    grade: Mapped[str] = mapped_column(String(4), nullable=False)
    # Privacy-processing consent (legal guardian for under-14s) confirmed by staff.
    consent_at: Mapped[datetime] = timestamp_column(nullable=False)
    # Separate consent or legal basis for sensitive (health/family) information.
    sensitive_basis_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    created_at: Mapped[datetime] = timestamp_column(nullable=False)


class Assignment(Base):
    __tablename__ = "assignment"
    __table_args__ = (
        CheckConstraint("start_date <= end_date", name="period"),
        Index("ix_assignment_mentor_child", "mentor_id", "child_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    mentor_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    # NULL after the child is destroyed: the row stays (revoked) as account history.
    child_id: Mapped[int | None] = mapped_column(ForeignKey("child.id"), nullable=True, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    revoked_at: Mapped[datetime | None] = timestamp_column(nullable=True)
    revoked_by: Mapped[int | None] = mapped_column(ForeignKey("app_user.id"), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("app_user.id"), nullable=False)
    created_at: Mapped[datetime] = timestamp_column(nullable=False)


# A mentor cannot hold two live (non-revoked) assignments for the same child
# whose periods overlap, so revoking one assignment always closes access.
Assignment.__table__.append_constraint(
    ExcludeConstraint(
        (Assignment.mentor_id, "="),
        (Assignment.child_id, "="),
        (func.daterange(Assignment.start_date, Assignment.end_date, literal("[]")), "&&"),
        name="ex_assignment_no_overlap",
        using="gist",
        where=Assignment.revoked_at.is_(None),
    )
)
