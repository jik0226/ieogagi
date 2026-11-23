"""Audit log search for director/staff (own center only, bounded paging)."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import KST
from app.models import AppUser, AuditLog
from app.schemas.common import ResponseModel


class AuditLogOut(ResponseModel):
    id: int
    actor_id: int | None
    action: str
    target_type: str | None
    target_id: int | None
    result: str
    ip: str | None
    detail: dict[str, Any]
    created_at: datetime


class AuditPageOut(ResponseModel):
    items: list[AuditLogOut]
    total: int


def _kst_day_start(day: date) -> datetime:
    return datetime.combine(day, time.min, tzinfo=KST)


def search_audit_logs(
    db: Session,
    *,
    actor: AppUser,
    action: str | None,
    result: str | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
) -> AuditPageOut:
    conditions = [AuditLog.center_id == actor.center_id]
    if action:
        conditions.append(AuditLog.action == action)
    if result:
        conditions.append(AuditLog.result == result)
    if date_from:
        conditions.append(AuditLog.created_at >= _kst_day_start(date_from))
    if date_to:
        conditions.append(AuditLog.created_at < _kst_day_start(date_to + timedelta(days=1)))
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*conditions)) or 0
    logs = db.scalars(
        select(AuditLog)
        .where(*conditions)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return AuditPageOut(items=[AuditLogOut.model_validate(log) for log in logs], total=total)
