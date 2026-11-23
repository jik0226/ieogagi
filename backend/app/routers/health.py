"""Liveness endpoint (no database or version details are exposed)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.authz.deps import public_endpoint

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", dependencies=[Depends(public_endpoint)])
def health_route() -> dict[str, str]:
    return {"status": "ok"}
