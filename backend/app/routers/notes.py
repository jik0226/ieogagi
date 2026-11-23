"""Staff note routes (F7) and audit log search (F10)."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request, status

from app.audit.writer import AuditorDep
from app.authz.deps import StaffChildAccess, StaffChildWriteAccess, StaffUser, route_template
from app.clock import ClockDep
from app.db import DbSession
from app.schemas.common import MAX_DATE, MIN_DATE, IdPath
from app.schemas.records import NoteCreateRequest, NoteDetailOut, NoteSummaryOut
from app.services.audit_query import AuditPageOut, search_audit_logs
from app.services.notes import create_note, list_notes, read_note

router = APIRouter(prefix="/api", tags=["notes", "audit"])


@router.post(
    "/children/{child_id}/notes", response_model=NoteSummaryOut, status_code=status.HTTP_201_CREATED
)
def create_note_route(
    request: Request,
    payload: NoteCreateRequest,
    access: StaffChildWriteAccess,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> NoteSummaryOut:
    return create_note(
        db,
        access=access,
        payload=payload,
        keyring=request.app.state.secrets.keyring,
        clock=clock,
        auditor=auditor,
    )


@router.get("/children/{child_id}/notes", response_model=list[NoteSummaryOut])
def list_notes_route(access: StaffChildAccess, db: DbSession) -> list[NoteSummaryOut]:
    return list_notes(db, access=access)


@router.get("/notes/{note_id}", response_model=NoteDetailOut)
def read_note_route(
    request: Request,
    note_id: IdPath,
    user: StaffUser,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> NoteDetailOut:
    return read_note(
        db,
        user=user,
        note_id=note_id,
        keyring=request.app.state.secrets.keyring,
        clock=clock,
        auditor=auditor,
        attempted=route_template(request),
    )


ActionFilter = Annotated[str | None, Query(pattern=r"^[a-z_]{2,20}\.[a-z_]{2,20}$")]
ResultFilter = Annotated[Literal["success", "denied", "failure"] | None, Query()]


@router.get("/audit-logs", response_model=AuditPageOut)
def audit_logs_route(
    user: StaffUser,
    db: DbSession,
    auditor: AuditorDep,
    action: ActionFilter = None,
    result: ResultFilter = None,
    date_from: Annotated[date | None, Query(ge=MIN_DATE, le=MAX_DATE)] = None,
    date_to: Annotated[date | None, Query(ge=MIN_DATE, le=MAX_DATE)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
) -> AuditPageOut:
    page = search_audit_logs(
        db,
        actor=user,
        action=action,
        result=result,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    auditor.stage(db, actor=user, action="audit.view", detail={"offset": offset})
    db.commit()
    return page
