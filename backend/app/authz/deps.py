"""Authorization dependencies used by every route.

Each route function must declare exactly one of these as a parameter type
(or mark itself public with ``dependencies=[Depends(public_endpoint)]``).
The custom Semgrep rule ``security/semgrep/fastapi-authz.yml`` fails the
build when a route has neither, so a forgotten check cannot ship.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request

from app.audit.writer import AuditorDep
from app.auth.deps import CurrentUser
from app.authz.policy import ChildAccess, authorize_child, deny
from app.clock import ClockDep
from app.db import DbSession
from app.models import STAFF_ROLES, AppUser, Role
from app.schemas.common import IdPath


def public_endpoint() -> None:
    """Marker dependency: the route is intentionally reachable without login."""


def route_template(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "unknown")


def require_roles(*roles: Role) -> Callable[..., AppUser]:
    allowed = frozenset(roles)

    def dependency(
        user: CurrentUser, db: DbSession, auditor: AuditorDep, request: Request
    ) -> AppUser:
        if user.role_enum not in allowed:
            raise deny(
                auditor,
                db,
                user=user,
                attempted=route_template(request),
                target_type=None,
                target_id=None,
                detail={"reason": "role"},
            )
        return user

    return dependency


def _child_access(allowed: frozenset[Role], *, lock: bool = False) -> Callable[..., ChildAccess]:
    def dependency(
        child_id: IdPath,
        user: CurrentUser,
        db: DbSession,
        clock: ClockDep,
        auditor: AuditorDep,
        request: Request,
    ) -> ChildAccess:
        return authorize_child(
            db,
            user=user,
            child_id=child_id,
            today=clock.today_kst(),
            auditor=auditor,
            allowed_roles=allowed,
            attempted=route_template(request),
            lock=lock,
        )

    return dependency


StaffUser = Annotated[AppUser, Depends(require_roles(Role.DIRECTOR, Role.STAFF))]
DirectorUser = Annotated[AppUser, Depends(require_roles(Role.DIRECTOR))]
MentorUser = Annotated[AppUser, Depends(require_roles(Role.MENTOR))]

MentorChildAccess = Annotated[ChildAccess, Depends(_child_access(frozenset({Role.MENTOR})))]
# Write paths hold a shared lock on the assignment row until commit, so a
# concurrent revoke cannot slip in between the check and the write.
MentorChildWriteAccess = Annotated[
    ChildAccess, Depends(_child_access(frozenset({Role.MENTOR}), lock=True))
]
StaffChildAccess = Annotated[ChildAccess, Depends(_child_access(STAFF_ROLES))]
# Staff inserts that reference the child (notes) hold a shared lock on the
# child row until commit, so a concurrent destruction cannot hit a foreign-key
# error halfway. Use only for inserts: a later UPDATE of the same child row
# would have to upgrade the shared lock.
StaffChildWriteAccess = Annotated[ChildAccess, Depends(_child_access(STAFF_ROLES, lock=True))]
DirectorChildAccess = Annotated[ChildAccess, Depends(_child_access(frozenset({Role.DIRECTOR})))]
ChildReadAccess = Annotated[ChildAccess, Depends(_child_access(frozenset(Role)))]
