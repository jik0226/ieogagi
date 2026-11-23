"""Mentor home, handover card and session record routes (F4, F5, F6, F8)."""

from __future__ import annotations

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter

from app.audit.writer import AuditorDep
from app.authz.deps import (
    ChildReadAccess,
    MentorChildAccess,
    MentorChildWriteAccess,
    MentorUser,
    StaffUser,
    route_template,
)
from app.clock import ClockDep
from app.db import DbSession
from app.schemas.children import MyAssignmentOut
from app.schemas.common import IdPath
from app.schemas.records import (
    CorrectionRequest,
    HandoverCardOut,
    HideRequest,
    MentorRecordOut,
    RecordCreateRequest,
    RedactRequest,
    StaffRecordOut,
)
from app.services.assignments import my_assignments
from app.services.record_moderation import hide_record, redact_record
from app.services.record_queries import handover_card, mentor_records, staff_records
from app.services.records import correct_record, create_record

router = APIRouter(prefix="/api", tags=["records"])


@router.get("/me/assignments", response_model=list[MyAssignmentOut])
def my_assignments_route(user: MentorUser, db: DbSession, clock: ClockDep) -> list[MyAssignmentOut]:
    return my_assignments(db, mentor=user, today=clock.today_kst())


@router.get("/children/{child_id}/handover-card", response_model=HandoverCardOut)
def handover_card_route(
    access: MentorChildAccess, db: DbSession, auditor: AuditorDep
) -> HandoverCardOut:
    card = handover_card(db, access=access)
    auditor.stage(
        db,
        actor=access.user,
        action="handover.view",
        target_type="child",
        target_id=access.child_id,
        detail={"records": len(card.records)},
    )
    db.commit()
    return card


# The declared union only documents both shapes. Each branch serializes
# through its own fixed schema, so a mentor response can never carry staff-only
# fields even if a staff object reached the mentor branch by mistake.
MENTOR_RECORD_LIST = TypeAdapter(list[MentorRecordOut])
STAFF_RECORD_LIST = TypeAdapter(list[StaffRecordOut])


@router.get(
    "/children/{child_id}/records", response_model=list[MentorRecordOut] | list[StaffRecordOut]
)
def list_records_route(access: ChildReadAccess, db: DbSession, auditor: AuditorDep) -> JSONResponse:
    if access.is_mentor:
        records = mentor_records(db, access=access)
        body = MENTOR_RECORD_LIST.dump_python(records, mode="json")
    else:
        staff_view = staff_records(db, access=access)
        body = STAFF_RECORD_LIST.dump_python(staff_view, mode="json")
    auditor.stage(
        db,
        actor=access.user,
        action="record.view",
        target_type="child",
        target_id=access.child_id,
        detail={"count": len(body)},
    )
    db.commit()
    return JSONResponse(body)


@router.post(
    "/children/{child_id}/records",
    response_model=MentorRecordOut,
    status_code=status.HTTP_201_CREATED,
)
def create_record_route(
    payload: RecordCreateRequest,
    access: MentorChildWriteAccess,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> MentorRecordOut:
    return create_record(db, access=access, payload=payload, clock=clock, auditor=auditor)


@router.post(
    "/records/{record_id}/corrections",
    response_model=MentorRecordOut,
    status_code=status.HTTP_201_CREATED,
)
def correct_record_route(
    request: Request,
    record_id: IdPath,
    payload: CorrectionRequest,
    user: MentorUser,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> MentorRecordOut:
    return correct_record(
        db,
        user=user,
        record_id=record_id,
        payload=payload,
        clock=clock,
        auditor=auditor,
        attempted=route_template(request),
    )


@router.post("/records/{record_id}/hide", response_model=StaffRecordOut)
def hide_record_route(
    request: Request,
    record_id: IdPath,
    payload: HideRequest,
    user: StaffUser,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> StaffRecordOut:
    return hide_record(
        db,
        user=user,
        record_id=record_id,
        payload=payload,
        clock=clock,
        auditor=auditor,
        attempted=route_template(request),
    )


@router.post("/records/{record_id}/redact", response_model=StaffRecordOut)
def redact_record_route(
    request: Request,
    record_id: IdPath,
    payload: RedactRequest,
    user: StaffUser,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> StaffRecordOut:
    return redact_record(
        db,
        user=user,
        record_id=record_id,
        payload=payload,
        clock=clock,
        auditor=auditor,
        attempted=route_template(request),
    )
