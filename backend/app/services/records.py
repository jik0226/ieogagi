"""Write paths for records: create, correct (append-only), hide, redact."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.writer import Auditor
from app.authz.policy import ChildAccess, authorize_child, deny
from app.clock import Clock
from app.errors import Conflict, InvalidRequest, SensitiveConfirmRequired
from app.models import AppUser, AuditResult, Child, Record, Role
from app.schemas.records import (
    CorrectionRequest,
    MentorRecordOut,
    RecordCreateRequest,
)
from app.services.record_queries import is_superseded
from app.services.sensitive import detect_sensitive_categories

MENTOR_ONLY = frozenset({Role.MENTOR})


def authorize_record(
    db: Session,
    *,
    user: AppUser,
    record_id: int,
    today: date,
    auditor: Auditor,
    allowed_roles: frozenset[Role],
    attempted: str,
    lock: bool = False,
    lock_record: bool = False,
) -> tuple[Record, ChildAccess]:
    """Resolve a record id to its child, then apply the common authorization.

    ``lock_record`` takes ``FOR UPDATE`` on the record row before anything is
    checked, so a correction and a hide of the same record run one after the
    other and each sees the other's committed result. Writers lock the record
    first and the assignment second, the same order as child destruction.
    """
    stmt = (
        select(Record)
        .join(Child, Child.id == Record.child_id)
        .where(Record.id == record_id, Child.center_id == user.center_id)
    )
    if lock_record:
        stmt = stmt.with_for_update(of=Record).execution_options(populate_existing=True)
    record = db.scalar(stmt)
    if record is None:
        raise deny(
            auditor,
            db,
            user=user,
            attempted=attempted,
            target_type="record",
            target_id=record_id,
            detail={"reason": "other_center_or_missing"},
        )
    access = authorize_child(
        db,
        user=user,
        child_id=record.child_id,
        today=today,
        auditor=auditor,
        allowed_roles=allowed_roles,
        attempted=attempted,
        lock=lock,
    )
    return record, access


def _confirm_sensitive(
    db: Session,
    payload: RecordCreateRequest | CorrectionRequest,
    *,
    access: ChildAccess,
    auditor: Auditor,
) -> list[str]:
    categories = detect_sensitive_categories((payload.did, payload.stuck, payload.next_step))
    if categories and not payload.sensitive_confirmed:
        auditor.write_now(
            db,
            actor=access.user,
            action="record.sensitive_prompt",
            result=AuditResult.SUCCESS,
            target_type="child",
            target_id=access.child_id,
            detail={"categories": categories},
        )
        raise SensitiveConfirmRequired(categories=categories)
    return categories


def create_record(
    db: Session,
    *,
    access: ChildAccess,
    payload: RecordCreateRequest,
    clock: Clock,
    auditor: Auditor,
) -> MentorRecordOut:
    assignment = access.assignment
    if assignment is None:
        raise ValueError("record creation requires a mentor assignment")
    today = clock.today_kst()
    if not (assignment.start_date <= payload.session_date <= min(assignment.end_date, today)):
        raise InvalidRequest("회차 날짜는 배정 기간 안이면서 오늘 이전이어야 합니다.")
    categories = _confirm_sensitive(db, payload, access=access, auditor=auditor)
    record = Record(
        child_id=access.child_id,
        author_id=access.user.id,
        session_date=payload.session_date,
        did=payload.did,
        stuck=payload.stuck,
        next_step=payload.next_step,
        created_at=clock.now(),
    )
    db.add(record)
    db.flush()
    auditor.stage(
        db,
        actor=access.user,
        action="record.create",
        target_type="record",
        target_id=record.id,
        detail={"child_id": access.child_id, "sensitive_confirmed": categories},
    )
    db.commit()
    return MentorRecordOut.model_validate(record)


def correct_record(
    db: Session,
    *,
    user: AppUser,
    record_id: int,
    payload: CorrectionRequest,
    clock: Clock,
    auditor: Auditor,
    attempted: str,
) -> MentorRecordOut:
    target, access = authorize_record(
        db,
        user=user,
        record_id=record_id,
        today=clock.today_kst(),
        auditor=auditor,
        allowed_roles=MENTOR_ONLY,
        attempted=attempted,
        lock=True,
        lock_record=True,
    )
    assignment = access.assignment
    if assignment is None:
        raise ValueError("correction requires a mentor assignment")
    in_period = assignment.start_date <= target.session_date <= assignment.end_date
    if target.author_id != user.id or not in_period or target.hidden_at is not None:
        raise deny(
            auditor,
            db,
            user=user,
            attempted=attempted,
            target_type="record",
            target_id=record_id,
            detail={"reason": "not_own_record_in_period"},
        )
    if is_superseded(db, target.id):
        raise Conflict("이미 정정된 기록입니다. 최신 기록을 정정해 주세요.")
    categories = _confirm_sensitive(db, payload, access=access, auditor=auditor)
    correction = Record(
        child_id=target.child_id,
        author_id=user.id,
        session_date=target.session_date,
        did=payload.did,
        stuck=payload.stuck,
        next_step=payload.next_step,
        corrects_id=target.id,
        created_at=clock.now(),
    )
    db.add(correction)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()  # unique(corrects_id): a concurrent correction won the race
        raise Conflict("이미 정정된 기록입니다. 최신 기록을 정정해 주세요.") from exc
    auditor.stage(
        db,
        actor=user,
        action="record.correct",
        target_type="record",
        target_id=correction.id,
        detail={"corrects_id": target.id, "sensitive_confirmed": categories},
    )
    db.commit()
    return MentorRecordOut.model_validate(correction)
