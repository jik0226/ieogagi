"""Mentor assignments: create, list, revoke, and the mentor's own list."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Select, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.writer import Auditor
from app.authz.policy import deny
from app.clock import Clock
from app.errors import Conflict
from app.models import AppUser, Assignment, Child, Role
from app.schemas.children import (
    AssignmentCreateRequest,
    AssignmentOut,
    AssignmentStatus,
    ChildBriefOut,
    MyAssignmentOut,
)

ASSIGNMENT_LIST_LIMIT = 1000
MY_ASSIGNMENT_LIMIT = 200


def assignment_status(assignment: Assignment, today: date) -> AssignmentStatus:
    if assignment.revoked_at is not None:
        return "revoked"
    if today < assignment.start_date:
        return "upcoming"
    if today > assignment.end_date:
        return "ended"
    return "active"


def _with_names() -> Select:
    return (
        select(Assignment, AppUser.display_name, Child.alias)
        .join(AppUser, AppUser.id == Assignment.mentor_id)
        .join(Child, Child.id == Assignment.child_id)
    )


def _to_out(
    assignment: Assignment, mentor_name: str, child_alias: str, today: date
) -> AssignmentOut:
    return AssignmentOut(
        id=assignment.id,
        mentor_id=assignment.mentor_id,
        mentor_name=mentor_name,
        child_id=assignment.child_id,
        child_alias=child_alias,
        start_date=assignment.start_date,
        end_date=assignment.end_date,
        revoked_at=assignment.revoked_at,
        status=assignment_status(assignment, today),
    )


def create_assignment(
    db: Session,
    *,
    actor: AppUser,
    payload: AssignmentCreateRequest,
    clock: Clock,
    auditor: Auditor,
    attempted: str,
) -> AssignmentOut:
    mentor = db.scalar(
        select(AppUser).where(
            AppUser.id == payload.mentor_id,
            AppUser.center_id == actor.center_id,
            AppUser.role == Role.MENTOR.value,
            AppUser.disabled_at.is_(None),
        )
    )
    # Shared lock on the child row until commit (lock order: record -> assignment
    # -> child): a concurrent destruction waits for this insert, or this waits
    # for it and finds no child, instead of failing on the foreign key.
    child = db.scalar(
        select(Child)
        .where(Child.id == payload.child_id, Child.center_id == actor.center_id)
        .with_for_update(read=True)
    )
    if mentor is None or child is None:
        raise deny(
            auditor,
            db,
            user=actor,
            attempted=attempted,
            target_type="assignment",
            target_id=None,
            detail={
                "reason": "mentor_or_child_not_in_center",
                "mentor_id": payload.mentor_id,
                "child_id": payload.child_id,
            },
        )
    assignment = Assignment(
        mentor_id=mentor.id,
        child_id=child.id,
        start_date=payload.start_date,
        end_date=payload.end_date,
        created_by=actor.id,
        created_at=clock.now(),
    )
    db.add(assignment)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()  # ex_assignment_no_overlap: same mentor+child, overlapping live period
        raise Conflict("같은 멘토에게 이 아동의 기간이 겹치는 배정이 이미 있습니다.") from exc
    auditor.stage(
        db,
        actor=actor,
        action="assignment.create",
        target_type="assignment",
        target_id=assignment.id,
        detail={
            "mentor_id": mentor.id,
            "child_id": child.id,
            "period": f"{payload.start_date}~{payload.end_date}",
        },
    )
    db.commit()
    return _to_out(assignment, mentor.display_name, child.alias, clock.today_kst())


def list_assignments(
    db: Session, *, actor: AppUser, today: date, child_id: int | None, mentor_id: int | None
) -> list[AssignmentOut]:
    stmt = _with_names().where(Child.center_id == actor.center_id)
    if child_id is not None:
        stmt = stmt.where(Assignment.child_id == child_id)
    if mentor_id is not None:
        stmt = stmt.where(Assignment.mentor_id == mentor_id)
    rows = db.execute(
        stmt.order_by(Assignment.start_date.desc(), Assignment.id.desc()).limit(
            ASSIGNMENT_LIST_LIMIT
        )
    ).all()
    return [_to_out(a, name, alias, today) for a, name, alias in rows]


def revoke_assignment(
    db: Session,
    *,
    actor: AppUser,
    assignment_id: int,
    clock: Clock,
    auditor: Auditor,
    attempted: str,
) -> AssignmentOut:
    row = db.execute(
        _with_names().where(Assignment.id == assignment_id, Child.center_id == actor.center_id)
    ).one_or_none()
    if row is None:
        raise deny(
            auditor,
            db,
            user=actor,
            attempted=attempted,
            target_type="assignment",
            target_id=assignment_id,
            detail={"reason": "other_center_or_missing"},
        )
    now = clock.now()
    revoked = db.execute(
        update(Assignment)
        .where(Assignment.id == assignment_id, Assignment.revoked_at.is_(None))
        .values(revoked_at=now, revoked_by=actor.id)
        .returning(Assignment.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if revoked is None:
        raise Conflict("이미 회수된 배정입니다.")
    auditor.stage(
        db,
        actor=actor,
        action="assignment.revoke",
        target_type="assignment",
        target_id=assignment_id,
        detail={"mentor_id": row[0].mentor_id},
    )
    db.commit()
    db.refresh(row[0])
    return _to_out(row[0], row[1], row[2], clock.today_kst())


def my_assignments(db: Session, *, mentor: AppUser, today: date) -> list[MyAssignmentOut]:
    rows = db.execute(
        select(Assignment, Child)
        .join(Child, Child.id == Assignment.child_id)
        .where(
            Assignment.mentor_id == mentor.id,
            Child.center_id == mentor.center_id,
            Assignment.revoked_at.is_(None),
            Assignment.end_date >= today,
        )
        .order_by(Assignment.start_date, Assignment.id)
        .limit(MY_ASSIGNMENT_LIMIT)
    ).all()
    return [
        MyAssignmentOut(
            assignment_id=a.id,
            child=ChildBriefOut.model_validate(child),
            start_date=a.start_date,
            end_date=a.end_date,
            status="upcoming" if today < a.start_date else "active",
        )
        for a, child in rows
    ]
