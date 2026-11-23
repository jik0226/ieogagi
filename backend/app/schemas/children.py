"""Schemas for children and assignments."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import field_validator, model_validator

from app.schemas.common import ChildAlias, DateValue, Grade, IdField, RequestModel, ResponseModel

MAX_ASSIGNMENT_DAYS = 366


class ChildCreateRequest(RequestModel):
    alias: ChildAlias
    grade: Grade
    privacy_consent_confirmed: bool
    sensitive_basis_confirmed: bool = False

    @field_validator("privacy_consent_confirmed")
    @classmethod
    def consent_required(cls, value: bool) -> bool:
        if not value:
            raise ValueError("개인정보 처리 동의를 확인해야 아동을 등록할 수 있습니다.")
        return value


class ChildOut(ResponseModel):
    id: int
    alias: str
    grade: str
    consent_at: datetime
    sensitive_basis_at: datetime | None
    created_at: datetime


class ChildBriefOut(ResponseModel):
    id: int
    alias: str
    grade: str


class AssignmentCreateRequest(RequestModel):
    mentor_id: IdField
    child_id: IdField
    start_date: DateValue
    end_date: DateValue

    @model_validator(mode="after")
    def check_period(self) -> AssignmentCreateRequest:
        if self.start_date > self.end_date:
            raise ValueError("시작일은 종료일보다 늦을 수 없습니다.")
        if (self.end_date - self.start_date).days > MAX_ASSIGNMENT_DAYS:
            raise ValueError("배정 기간은 366일을 넘을 수 없습니다.")
        return self


AssignmentStatus = Literal["upcoming", "active", "ended", "revoked"]


class AssignmentOut(ResponseModel):
    id: int
    mentor_id: int
    mentor_name: str
    child_id: int
    child_alias: str
    start_date: date
    end_date: date
    revoked_at: datetime | None
    status: AssignmentStatus


class MyAssignmentOut(ResponseModel):
    assignment_id: int
    child: ChildBriefOut
    start_date: date
    end_date: date
    status: Literal["upcoming", "active"]
