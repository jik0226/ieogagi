"""Audit log writer.

Two write modes, both on the request's own DB session (one connection per
request, so audit writes can never exhaust the connection pool):
- ``stage``: the row joins the current transaction, so a change and its
  audit record are committed (or rolled back) together.
- ``write_now``: for denied or failed attempts. The pending transaction is
  rolled back first (nothing from a refused request may persist), then only
  the audit row is inserted and committed, so the trace always survives.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.clock import Clock
from app.models import AppUser, AuditLog, AuditResult


@dataclass(frozen=True)
class Auditor:
    clock: Clock
    ip: str | None

    def _build(
        self,
        *,
        actor: AppUser | None,
        action: str,
        result: AuditResult,
        target_type: str | None,
        target_id: int | None,
        detail: dict[str, Any] | None,
        center_id: int | None,
    ) -> AuditLog:
        return AuditLog(
            center_id=center_id if center_id is not None else (actor.center_id if actor else None),
            actor_id=actor.id if actor else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            result=result.value,
            ip=self.ip,
            detail=detail or {},
            created_at=self.clock.now(),
        )

    def stage(
        self,
        db: Session,
        *,
        actor: AppUser | None,
        action: str,
        target_type: str | None = None,
        target_id: int | None = None,
        detail: dict[str, Any] | None = None,
        result: AuditResult = AuditResult.SUCCESS,
        center_id: int | None = None,
    ) -> None:
        db.add(
            self._build(
                actor=actor,
                action=action,
                result=result,
                target_type=target_type,
                target_id=target_id,
                detail=detail,
                center_id=center_id,
            )
        )

    def write_now(
        self,
        db: Session,
        *,
        actor: AppUser | None,
        action: str,
        result: AuditResult,
        target_type: str | None = None,
        target_id: int | None = None,
        detail: dict[str, Any] | None = None,
        center_id: int | None = None,
    ) -> None:
        # Build first: reading actor attributes after rollback would re-query.
        row = self._build(
            actor=actor,
            action=action,
            result=result,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
            center_id=center_id,
        )
        db.rollback()
        db.add(row)
        db.commit()


def client_ip(request: Request) -> str | None:
    # uvicorn rewrites request.client from X-Forwarded-For only for proxies
    # listed in --forwarded-allow-ips, so this is never a client-chosen value.
    return request.client.host if request.client else None


def get_auditor(request: Request) -> Auditor:
    return Auditor(clock=request.app.state.clock, ip=client_ip(request))


AuditorDep = Annotated[Auditor, Depends(get_auditor)]
