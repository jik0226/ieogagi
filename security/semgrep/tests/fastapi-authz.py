# Test cases for ieogagi-route-missing-authz (fixtures, not application code).
from fastapi import APIRouter, Depends, Request

from app.authz.deps import (
    ChildReadAccess,
    CurrentUser,
    MentorUser,
    StaffChildWriteAccess,
    StaffUser,
    public_endpoint,
)
from app.security.ratelimit import limiter

router = APIRouter()


# ruleid: ieogagi-route-missing-authz
@router.get("/api/children")
def list_children_unprotected(db: object) -> list:
    return []


# ruleid: ieogagi-route-missing-authz
@router.post("/api/records/{record_id}/hide")
def hide_with_plain_int(record_id: int, user: object) -> dict:
    return {}


# ruleid: ieogagi-route-missing-authz
@router.post("/api/auth/login")
@limiter.limit("10/minute")
def login_without_marker(request: Request) -> dict:
    return {}


# ok: ieogagi-route-missing-authz
@router.get("/api/users")
def list_users(user: StaffUser) -> list:
    return []


# ok: ieogagi-route-missing-authz
@router.get("/api/children/{child_id}/records")
def list_records(access: ChildReadAccess, db: object) -> list:
    return []


# ok: ieogagi-route-missing-authz
@router.post("/api/children/{child_id}/notes", status_code=201)
def create_note(payload: dict, access: StaffChildWriteAccess) -> dict:
    return {}


# ok: ieogagi-route-missing-authz
@router.post("/api/records/{record_id}/corrections", status_code=201)
def correct(request: Request, record_id: int, user: MentorUser) -> dict:
    return {}


# ok: ieogagi-route-missing-authz
@router.post("/api/auth/login", dependencies=[Depends(public_endpoint)])
@limiter.limit("10/minute")
def login(request: Request) -> dict:
    return {}


# ok: ieogagi-route-missing-authz
@router.get("/api/health", dependencies=[Depends(public_endpoint)])
def health() -> dict:
    return {}


# ok: ieogagi-route-missing-authz
def helper_without_decorator(value: int) -> int:
    return value


# ruleid: ieogagi-route-missing-authz
@router.get("/api/async/children")
async def list_children_async_unprotected(db: object) -> list:
    return []


# ruleid: ieogagi-route-missing-authz
@router.websocket("/ws/updates")
async def updates_unprotected(websocket: object) -> None:
    return None


# ruleid: ieogagi-route-missing-authz
@router.head("/api/children")
def head_unprotected() -> None:
    return None


# ruleid: ieogagi-route-missing-authz
@router.options("/api/children")
def options_unprotected() -> None:
    return None


# ruleid: ieogagi-route-missing-authz
@router.trace("/api/children")
def trace_unprotected() -> None:
    return None


# ok: ieogagi-route-missing-authz
@router.get("/api/async/users")
async def list_users_async(user: StaffUser) -> list:
    return []


# ok: ieogagi-route-missing-authz
@router.get("/api/async/mine")
async def mine_async(user: CurrentUser, db: object) -> dict:
    return {}


# ok: ieogagi-route-missing-authz
@router.get("/api/async/health", dependencies=[Depends(public_endpoint)])
async def health_async() -> dict:
    return {}


# ok: ieogagi-route-missing-authz
@router.websocket("/ws/private")
async def updates_private(websocket: object, user: CurrentUser) -> None:
    return None


# ok: ieogagi-route-missing-authz
@router.websocket("/ws/public", dependencies=[Depends(public_endpoint)])
async def updates_public(websocket: object) -> None:
    return None
