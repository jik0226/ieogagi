"""Schemas for authentication and accounts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import field_validator

from app.schemas.common import (
    InviteCode,
    LoginId,
    PasswordInput,
    PersonName,
    RequestModel,
    ResponseModel,
)
from app.security.passwords import password_policy_violation

RoleName = Literal["director", "staff", "mentor"]


class InviteVerifyRequest(RequestModel):
    code: InviteCode


class InviteVerifyOut(ResponseModel):
    role: RoleName
    center_name: str
    expires_at: datetime


class SignupRequest(RequestModel):
    code: InviteCode
    login_id: LoginId
    display_name: PersonName
    password: PasswordInput

    @field_validator("password")
    @classmethod
    def check_policy(cls, value: str) -> str:
        violation = password_policy_violation(value)
        if violation is not None:
            raise ValueError(violation)
        return value


class LoginRequest(RequestModel):
    login_id: LoginId
    password: PasswordInput


class CenterOut(ResponseModel):
    id: int
    name: str


class MeOut(ResponseModel):
    id: int
    login_id: str
    display_name: str
    role: RoleName
    center: CenterOut


class InviteCreateRequest(RequestModel):
    role: Literal["staff", "mentor"]


class InviteCreatedOut(ResponseModel):
    code: str
    role: RoleName
    expires_at: datetime


class UserSummaryOut(ResponseModel):
    id: int
    login_id: str
    display_name: str
    role: RoleName
    disabled_at: datetime | None
    assignment_ended: bool
