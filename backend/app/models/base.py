"""Declarative base, shared enums and column helpers."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import DateTime, MetaData
from sqlalchemy.orm import DeclarativeBase, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Role(StrEnum):
    DIRECTOR = "director"  # facility head (시설장)
    STAFF = "staff"  # social worker in charge (담당자)
    MENTOR = "mentor"  # volunteer tutor (멘토)


STAFF_ROLES = frozenset({Role.DIRECTOR, Role.STAFF})


class HideReason(StrEnum):
    INAPPROPRIATE = "INAPPROPRIATE"
    WRONG_CHILD = "WRONG_CHILD"
    DUPLICATE = "DUPLICATE"
    SENSITIVE = "SENSITIVE"
    OTHER = "OTHER"


class AuditResult(StrEnum):
    SUCCESS = "success"
    DENIED = "denied"
    FAILURE = "failure"


def timestamp_column(*, nullable: bool):
    """Timezone-aware timestamp. Values are always set by the app clock."""
    return mapped_column(DateTime(timezone=True), nullable=nullable)


__all__ = [
    "STAFF_ROLES",
    "AuditResult",
    "Base",
    "HideReason",
    "Role",
    "timestamp_column",
]
