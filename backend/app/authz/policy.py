"""The common authorization function for child-scoped resources.

"The assignment period IS the access right." Every API that touches a
child's records, handover card or notes goes through ``authorize_child``.

- Mentor: allowed only if ONE SQL query finds an assignment satisfying
  same center AND own assignment AND start_date <= today <= end_date AND
  not revoked. ``today`` is the Korea date computed by the app and bound as a
  parameter. Nothing is cached in tokens, so expiry or revocation takes
  effect on the very next request.
- Director/staff: allowed if the child belongs to their own center.

Denials are written to the audit log in a separate transaction and surface
as a generic 403 (the response never says *why*, the audit log does).

Row lock order, the same for every writer so no two can wait on each other
in a cycle: record rows -> assignment rows -> child row. ``lock=True`` takes
the lock that a write path needs before inserting a row that references the
child: a shared lock on the mentor's assignment row, or on the child row
itself for staff (who have no assignment). Child destruction takes all three
with FOR UPDATE in that order (``services/children.py``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.writer import Auditor
from app.errors import Forbidden
from app.models import STAFF_ROLES, AppUser, Assignment, AuditResult, Child, Role


@dataclass(frozen=True)
class ChildAccess:
    user: AppUser
    child_id: int
    assignment: Assignment | None  # set when the requester is a mentor

    @property
    def is_mentor(self) -> bool:
        return self.assignment is not None


def find_active_assignment(
    db: Session, *, mentor: AppUser, child_id: int, today: date, lock: bool = False
) -> Assignment | None:
    """Single-query period check. ``lock`` takes a shared row lock (write paths),
    so a concurrent revoke or child destruction waits until the write that
    relied on it commits, or this query waits for them and finds nothing."""
    stmt = (
        select(Assignment)
        .join(Child, Child.id == Assignment.child_id)
        .where(
            Assignment.child_id == child_id,
            Assignment.mentor_id == mentor.id,
            Child.center_id == mentor.center_id,
            Assignment.start_date <= today,
            Assignment.end_date >= today,
            Assignment.revoked_at.is_(None),
        )
        .order_by(Assignment.start_date.desc())
        .limit(1)
    )
    if lock:
        stmt = stmt.with_for_update(read=True, of=Assignment)
    return db.scalar(stmt)


def _denial_detail(db: Session, *, mentor: AppUser, child_id: int, today: date) -> dict[str, Any]:
    """Classify why a mentor was denied (audit detail only, never sent to the client)."""
    latest = db.scalar(
        select(Assignment)
        .join(Child, Child.id == Assignment.child_id)
        .where(
            Assignment.child_id == child_id,
            Assignment.mentor_id == mentor.id,
            Child.center_id == mentor.center_id,
        )
        .order_by(Assignment.end_date.desc())
        .limit(1)
    )
    if latest is None:
        return {"reason": "not_assigned"}
    period = f"{latest.start_date.isoformat()}~{latest.end_date.isoformat()}"
    if latest.revoked_at is not None:
        reason = "revoked"
    elif today < latest.start_date:
        reason = "before_start"
    else:
        reason = "after_end"
    return {"reason": reason, "period": period, "assignment_id": latest.id}


def deny(
    auditor: Auditor,
    db: Session,
    *,
    user: AppUser,
    attempted: str,
    target_type: str | None,
    target_id: int | None,
    detail: dict[str, Any],
) -> Forbidden:
    """Record the denial and return the error for the caller to ``raise``.

    Returning (instead of raising inside) keeps the control flow explicit at
    every call site: ``raise deny(...)``.
    """
    auditor.write_now(
        db,
        actor=user,
        action="access.denied",
        result=AuditResult.DENIED,
        target_type=target_type,
        target_id=target_id,
        detail={"attempted": attempted, **detail},
    )
    return Forbidden()


def authorize_child(
    db: Session,
    *,
    user: AppUser,
    child_id: int,
    today: date,
    auditor: Auditor,
    allowed_roles: frozenset[Role],
    attempted: str,
    lock: bool = False,
) -> ChildAccess:
    role = user.role_enum
    if role not in allowed_roles:
        raise deny(
            auditor,
            db,
            user=user,
            attempted=attempted,
            target_type="child",
            target_id=child_id,
            detail={"reason": "role"},
        )
    if role in STAFF_ROLES:
        stmt = select(Child.id).where(Child.id == child_id, Child.center_id == user.center_id)
        if lock:
            # Shared lock on the child row until commit: a concurrent destruction
            # waits for this write, or this check waits for it and finds no child.
            stmt = stmt.with_for_update(read=True)
        same_center = db.scalar(stmt)
        if same_center is None:
            raise deny(
                auditor,
                db,
                user=user,
                attempted=attempted,
                target_type="child",
                target_id=child_id,
                detail={"reason": "other_center_or_missing"},
            )
        return ChildAccess(user=user, child_id=child_id, assignment=None)
    assignment = find_active_assignment(db, mentor=user, child_id=child_id, today=today, lock=lock)
    if assignment is None:
        raise deny(
            auditor,
            db,
            user=user,
            attempted=attempted,
            target_type="child",
            target_id=child_id,
            detail=_denial_detail(db, mentor=user, child_id=child_id, today=today),
        )
    return ChildAccess(user=user, child_id=child_id, assignment=assignment)
