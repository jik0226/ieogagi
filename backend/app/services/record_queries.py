"""Read paths for records: handover card, mentor view, staff view.

"Effective" records are the ones a mentor may ever see: not hidden and not
superseded by a correction. Mentor queries always apply that filter and
always bound dates by the requester's assignment, so the visible set is
exactly: the 4 latest records before the assignment start (handover card)
plus the mentor's own records within the assignment period.
"""

from __future__ import annotations

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, aliased

from app.authz.policy import ChildAccess
from app.models import AppUser, Child, Record, StaffNote
from app.schemas.children import ChildBriefOut
from app.schemas.records import (
    AuthorOut,
    CardPeriodOut,
    CardRecordOut,
    HandoverCardOut,
    MentorRecordOut,
    StaffRecordOut,
)

HANDOVER_RECORD_COUNT = 4
SHARE_TEXT_LIMIT = 10
STAFF_RECORD_LIMIT = 500
MENTOR_RECORD_LIMIT = 500

_Successor = aliased(Record)


def superseded_expr():
    # Only a visible correction replaces a record; a correction hidden by staff
    # makes the corrected record visible (and correctable) again.
    return exists().where(_Successor.corrects_id == Record.id, _Successor.hidden_at.is_(None))


def effective_filter():
    return Record.hidden_at.is_(None) & ~superseded_expr()


def handover_card(db: Session, *, access: ChildAccess) -> HandoverCardOut:
    assignment = access.assignment
    if assignment is None:
        raise ValueError("handover card requires a mentor assignment")
    numbered = (
        select(
            Record.id.label("id"),
            Record.session_date.label("session_date"),
            Record.did.label("did"),
            Record.stuck.label("stuck"),
            Record.next_step.label("next_step"),
            func.row_number().over(order_by=(Record.session_date, Record.id)).label("session_no"),
        )
        .where(
            Record.child_id == access.child_id,
            Record.session_date < assignment.start_date,
            effective_filter(),
        )
        .subquery()
    )
    rows = db.execute(
        select(numbered).order_by(numbered.c.session_no.desc()).limit(HANDOVER_RECORD_COUNT)
    ).all()
    share_texts = db.scalars(
        select(StaffNote.share_text)
        .where(StaffNote.child_id == access.child_id, StaffNote.share_text.is_not(None))
        .order_by(StaffNote.created_at.desc(), StaffNote.id.desc())
        .limit(SHARE_TEXT_LIMIT)
    ).all()
    child = db.get(Child, access.child_id)
    return HandoverCardOut(
        child=ChildBriefOut.model_validate(child),
        assignment=CardPeriodOut(start_date=assignment.start_date, end_date=assignment.end_date),
        records=[
            CardRecordOut(
                session_no=row.session_no,
                session_date=row.session_date,
                did=row.did,
                stuck=row.stuck,
                next_step=row.next_step,
            )
            for row in rows
        ],
        share_texts=[text for text in share_texts if text],
    )


def mentor_records(db: Session, *, access: ChildAccess) -> list[MentorRecordOut]:
    assignment = access.assignment
    if assignment is None:
        raise ValueError("mentor records require a mentor assignment")
    records = db.scalars(
        select(Record)
        .where(
            Record.child_id == access.child_id,
            Record.author_id == access.user.id,
            Record.session_date >= assignment.start_date,
            Record.session_date <= assignment.end_date,
            effective_filter(),
        )
        .order_by(Record.session_date.desc(), Record.id.desc())
        .limit(MENTOR_RECORD_LIMIT)
    ).all()
    return [MentorRecordOut.model_validate(record) for record in records]


def staff_records(db: Session, *, access: ChildAccess) -> list[StaffRecordOut]:
    # Same numbering as the handover card: effective records only, in session order.
    numbered = (
        select(
            Record.id.label("id"),
            func.row_number().over(order_by=(Record.session_date, Record.id)).label("session_no"),
        )
        .where(Record.child_id == access.child_id, effective_filter())
        .subquery()
    )
    rows = db.execute(
        select(
            Record,
            AppUser.display_name,
            superseded_expr().label("superseded"),
            numbered.c.session_no,
        )
        .join(AppUser, AppUser.id == Record.author_id)
        .outerjoin(numbered, numbered.c.id == Record.id)
        .where(Record.child_id == access.child_id)
        .order_by(Record.session_date.desc(), Record.id.desc())
        .limit(STAFF_RECORD_LIMIT)
    ).all()
    return [
        staff_record_out(record, name, superseded=bool(sup), session_no=number)
        for record, name, sup, number in rows
    ]


def staff_record_out(
    record: Record, author_name: str, *, superseded: bool, session_no: int | None = None
) -> StaffRecordOut:
    return StaffRecordOut(
        session_no=session_no,
        id=record.id,
        session_date=record.session_date,
        did=record.did,
        stuck=record.stuck,
        next_step=record.next_step,
        corrects_id=record.corrects_id,
        created_at=record.created_at,
        author=AuthorOut(id=record.author_id, display_name=author_name),
        hidden_at=record.hidden_at,
        hidden_reason_code=record.hidden_reason_code,
        redacted_at=record.redacted_at,
        superseded=superseded,
    )


def is_superseded(db: Session, record_id: int) -> bool:
    visible_successor = exists().where(Record.corrects_id == record_id, Record.hidden_at.is_(None))
    return db.scalar(select(visible_successor)) or False
