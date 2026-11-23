"""Child and assignment routes (F2, F3, F8 destruction)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from app.audit.writer import AuditorDep
from app.authz.deps import DirectorChildAccess, StaffChildAccess, StaffUser, route_template
from app.clock import ClockDep
from app.db import DbSession
from app.schemas.children import (
    AssignmentCreateRequest,
    AssignmentOut,
    ChildCreateRequest,
    ChildOut,
)
from app.schemas.common import MAX_ID, IdPath
from app.services.assignments import create_assignment, list_assignments, revoke_assignment
from app.services.children import (
    confirm_sensitive_basis,
    create_child,
    destroy_child,
    list_children,
)

router = APIRouter(prefix="/api", tags=["children"])
OptionalId = Annotated[int | None, Query(ge=1, le=MAX_ID)]


@router.post("/children", response_model=ChildOut, status_code=status.HTTP_201_CREATED)
def create_child_route(
    payload: ChildCreateRequest,
    user: StaffUser,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> ChildOut:
    return create_child(db, actor=user, payload=payload, clock=clock, auditor=auditor)


@router.get("/children", response_model=list[ChildOut])
def list_children_route(user: StaffUser, db: DbSession) -> list[ChildOut]:
    return list_children(db, actor=user)


@router.post("/children/{child_id}/sensitive-basis", response_model=ChildOut)
def confirm_sensitive_basis_route(
    access: StaffChildAccess, db: DbSession, clock: ClockDep, auditor: AuditorDep
) -> ChildOut:
    return confirm_sensitive_basis(db, access=access, clock=clock, auditor=auditor)


@router.delete("/children/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
def destroy_child_route(
    request: Request,
    access: DirectorChildAccess,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> Response:
    destroy_child(
        db, access=access, clock=clock, auditor=auditor, attempted=route_template(request)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment_route(
    request: Request,
    payload: AssignmentCreateRequest,
    user: StaffUser,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> AssignmentOut:
    return create_assignment(
        db,
        actor=user,
        payload=payload,
        clock=clock,
        auditor=auditor,
        attempted=route_template(request),
    )


@router.get("/assignments", response_model=list[AssignmentOut])
def list_assignments_route(
    user: StaffUser,
    db: DbSession,
    clock: ClockDep,
    child_id: OptionalId = None,
    mentor_id: OptionalId = None,
) -> list[AssignmentOut]:
    return list_assignments(
        db, actor=user, today=clock.today_kst(), child_id=child_id, mentor_id=mentor_id
    )


@router.post("/assignments/{assignment_id}/revoke", response_model=AssignmentOut)
def revoke_assignment_route(
    request: Request,
    assignment_id: IdPath,
    user: StaffUser,
    db: DbSession,
    clock: ClockDep,
    auditor: AuditorDep,
) -> AssignmentOut:
    return revoke_assignment(
        db,
        actor=user,
        assignment_id=assignment_id,
        clock=clock,
        auditor=auditor,
        attempted=route_template(request),
    )
