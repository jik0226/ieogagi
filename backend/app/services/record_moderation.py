"""Staff moderation of records: hide with a reason code, blank sensitive fields.

Rows are never deleted here; hidden rows stay visible to staff and the
change is written to the audit log in the same transaction.
"""

from __future__ import annotations

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.audit.writer import Auditor
from app.clock import Clock
from app.errors import Conflict
from app.models import STAFF_ROLES, AppUser, Record
from app.schemas.records import HideRequest, RedactRequest, StaffRecordOut
from app.services.record_queries import is_superseded, staff_record_out
from app.services.records import authorize_record


def hide_record(
    db: Session,
    *,
    user: AppUser,
    record_id: int,
    payload: HideRequest,
    clock: Clock,
    auditor: Auditor,
    attempted: str,
) -> StaffRecordOut:
    record, _ = authorize_record(
        db,
        user=user,
        record_id=record_id,
        today=clock.today_kst(),
        auditor=auditor,
        allowed_roles=STAFF_ROLES,
        attempted=attempted,
        lock_record=True,
    )
    hidden = db.execute(
        update(Record)
        .where(Record.id == record.id, Record.hidden_at.is_(None))
        .values(hidden_at=clock.now(), hidden_by=user.id, hidden_reason_code=payload.reason_code)
        .returning(Record.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if hidden is None:
        raise Conflict("이미 숨김 처리된 기록입니다.")
    auditor.stage(
        db,
        actor=user,
        action="record.hide",
        target_type="record",
        target_id=record.id,
        detail={"reason_code": payload.reason_code.value},
    )
    db.commit()
    return _reload_staff_record(db, record.id)


def redact_record(
    db: Session,
    *,
    user: AppUser,
    record_id: int,
    payload: RedactRequest,
    clock: Clock,
    auditor: Auditor,
    attempted: str,
) -> StaffRecordOut:
    record, _ = authorize_record(
        db,
        user=user,
        record_id=record_id,
        today=clock.today_kst(),
        auditor=auditor,
        allowed_roles=STAFF_ROLES,
        attempted=attempted,
        lock_record=True,
    )
    blanks = {field: "" for field in payload.fields}
    db.execute(
        update(Record)
        .where(Record.id == record.id)
        .values(**blanks, redacted_at=clock.now(), redacted_by=user.id)
        .execution_options(synchronize_session=False)
    )
    auditor.stage(
        db,
        actor=user,
        action="record.redact",
        target_type="record",
        target_id=record.id,
        detail={"fields": list(payload.fields)},
    )
    db.commit()
    return _reload_staff_record(db, record.id)


def _reload_staff_record(db: Session, record_id: int) -> StaffRecordOut:
    record = db.get(Record, record_id, populate_existing=True)
    if record is None:
        raise ValueError("record disappeared during update")
    author = db.get(AppUser, record.author_id)
    author_name = author.display_name if author is not None else ""
    return staff_record_out(record, author_name, superseded=is_superseded(db, record.id))
