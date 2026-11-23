"""Child registration, consent confirmation and destruction (director/staff)."""

from __future__ import annotations

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.audit.writer import Auditor
from app.authz.policy import ChildAccess, deny
from app.clock import Clock
from app.errors import Conflict
from app.models import AppUser, Assignment, Child, Record, StaffNote
from app.schemas.children import ChildCreateRequest, ChildOut

CHILD_LIST_LIMIT = 1000
DESTROY_LOCK_ATTEMPTS = 3
BUSY_MESSAGE = "이 아동의 기록을 다른 사용자가 고치고 있습니다. 잠시 후 다시 시도해 주세요."


def create_child(
    db: Session, *, actor: AppUser, payload: ChildCreateRequest, clock: Clock, auditor: Auditor
) -> ChildOut:
    now = clock.now()
    child = Child(
        center_id=actor.center_id,
        alias=payload.alias,
        grade=payload.grade,
        consent_at=now,
        sensitive_basis_at=now if payload.sensitive_basis_confirmed else None,
        created_by=actor.id,
        created_at=now,
    )
    db.add(child)
    db.flush()
    auditor.stage(
        db,
        actor=actor,
        action="child.create",
        target_type="child",
        target_id=child.id,
        detail={"sensitive_basis": payload.sensitive_basis_confirmed},
    )
    db.commit()
    return ChildOut.model_validate(child)


def list_children(db: Session, *, actor: AppUser) -> list[ChildOut]:
    children = db.scalars(
        select(Child)
        .where(Child.center_id == actor.center_id)
        .order_by(Child.alias, Child.id)
        .limit(CHILD_LIST_LIMIT)
    ).all()
    return [ChildOut.model_validate(child) for child in children]


def confirm_sensitive_basis(
    db: Session, *, access: ChildAccess, clock: Clock, auditor: Auditor
) -> ChildOut:
    now = clock.now()
    updated = db.execute(
        update(Child)
        .where(Child.id == access.child_id, Child.sensitive_basis_at.is_(None))
        .values(sensitive_basis_at=now)
        .returning(Child.id)
        .execution_options(synchronize_session=False)
    ).scalar_one_or_none()
    if updated is None:
        raise Conflict("이미 민감정보 확인이 된 아동입니다.")
    auditor.stage(
        db,
        actor=access.user,
        action="child.sensitive_basis",
        target_type="child",
        target_id=access.child_id,
    )
    db.commit()
    return ChildOut.model_validate(db.get(Child, access.child_id))


def _all_records_locked(db: Session, child_id: int) -> bool:
    """True if this transaction holds a lock on every record of the child.

    Takes the missing locks without waiting (SKIP LOCKED also returns rows this
    transaction already holds); a row another transaction holds is left out.
    """
    current = set(db.scalars(select(Record.id).where(Record.child_id == child_id)))
    locked = set(
        db.scalars(
            select(Record.id).where(Record.child_id == child_id).with_for_update(skip_locked=True)
        )
    )
    return locked == current


def _lock_for_destruction(db: Session, *, child_id: int, center_id: int) -> bool:
    """Lock every row destruction touches, in the global lock order.

    Lock order (all writers): record rows -> assignment rows -> child row.
    Corrections and hides lock their record first and the assignment second,
    record creation share-locks the assignment before its insert share-locks
    the child, and note creation share-locks the child. So an in-flight write
    commits before the deletes run (and is deleted with the rest), or it waits
    for this transaction and then finds no child.

    Once every assignment row is locked no record can be added, but a record
    committed while we waited for those locks was not in the first pass, and a
    correction may hold it while waiting for our assignment lock. Waiting for
    it would deadlock, so the attempt is rolled back to its savepoint (which
    releases our locks and lets the correction finish) and retried.
    Returns False if the child is gone (a concurrent destruction committed).
    """
    for _attempt in range(DESTROY_LOCK_ATTEMPTS):
        savepoint = db.begin_nested()
        db.scalars(
            select(Record.id)
            .where(Record.child_id == child_id)
            .order_by(Record.id)
            .with_for_update()
        ).all()
        db.scalars(
            select(Assignment.id)
            .where(Assignment.child_id == child_id)
            .order_by(Assignment.id)
            .with_for_update()
        ).all()
        if _all_records_locked(db, child_id):
            savepoint.commit()  # RELEASE SAVEPOINT: the locks stay with the transaction
            locked = db.scalar(
                select(Child.id)
                .where(Child.id == child_id, Child.center_id == center_id)
                .with_for_update()
            )
            return locked is not None
        savepoint.rollback()
    raise Conflict(BUSY_MESSAGE)


def destroy_child(
    db: Session, *, access: ChildAccess, clock: Clock, auditor: Auditor, attempted: str
) -> None:
    """Delete the child's records, notes and the child row.

    Assignments are detached (child_id -> NULL) and revoked rather than
    deleted: they no longer point at any child, but the mentor's account
    history keeps showing "assignment ended" so the account gets disabled.
    The audit history is kept (internal ids only) and the destruction itself
    is recorded in the same transaction.
    """
    child_id = access.child_id
    if not _lock_for_destruction(db, child_id=child_id, center_id=access.user.center_id):
        # A concurrent destruction committed while this one waited for the locks.
        raise deny(
            auditor,
            db,
            user=access.user,
            attempted=attempted,
            target_type="child",
            target_id=child_id,
            detail={"reason": "other_center_or_missing"},
        )
    now = clock.now()
    records = db.execute(delete(Record).where(Record.child_id == child_id)).rowcount
    notes = db.execute(delete(StaffNote).where(StaffNote.child_id == child_id)).rowcount
    assignments = db.execute(
        update(Assignment)
        .where(Assignment.child_id == child_id)
        .values(
            child_id=None,
            revoked_at=func.coalesce(Assignment.revoked_at, now),
            revoked_by=func.coalesce(Assignment.revoked_by, access.user.id),
        )
        .execution_options(synchronize_session=False)
    ).rowcount
    db.execute(delete(Child).where(Child.id == child_id))
    auditor.stage(
        db,
        actor=access.user,
        action="child.destroy",
        target_type="child",
        target_id=child_id,
        detail={"records": records, "notes": notes, "assignments": assignments},
    )
    db.commit()
