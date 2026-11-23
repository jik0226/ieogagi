"""Schemas for session records, handover cards and staff notes.

Mentor-facing response models are separate classes that simply do not have
fields for hidden rows, staff note bodies or ciphertext, so such data cannot
be serialized to a mentor even by mistake.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import Field, model_validator

from app.models import HideReason
from app.schemas.children import ChildBriefOut
from app.schemas.common import (
    DateValue,
    NoteBody,
    RecordText,
    RequestModel,
    ResponseModel,
    ShareText,
)

RecordField = Literal["did", "stuck", "next_step"]


class _RecordContent(RequestModel):
    did: RecordText = ""
    stuck: RecordText = ""
    next_step: RecordText = ""
    sensitive_confirmed: bool = False

    @model_validator(mode="after")
    def at_least_one_field(self) -> _RecordContent:
        if not (self.did or self.stuck or self.next_step):
            raise ValueError("세 칸 중 하나 이상 적어 주세요.")
        return self


class RecordCreateRequest(_RecordContent):
    session_date: DateValue


class CorrectionRequest(_RecordContent):
    pass


class HideRequest(RequestModel):
    reason_code: HideReason


class RedactRequest(RequestModel):
    fields: list[RecordField] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique_fields(self) -> RedactRequest:
        if len(set(self.fields)) != len(self.fields):
            raise ValueError("같은 칸을 두 번 지정할 수 없습니다.")
        return self


class AuthorOut(ResponseModel):
    id: int
    display_name: str


class MentorRecordOut(ResponseModel):
    id: int
    session_date: date
    did: str
    stuck: str
    next_step: str
    corrects_id: int | None
    created_at: datetime


class StaffRecordOut(MentorRecordOut):
    session_no: int | None = None  # cumulative session number; None for hidden/replaced rows
    author: AuthorOut
    hidden_at: datetime | None
    hidden_reason_code: str | None
    redacted_at: datetime | None
    superseded: bool


class CardRecordOut(ResponseModel):
    session_no: int
    session_date: date
    did: str
    stuck: str
    next_step: str


class CardPeriodOut(ResponseModel):
    start_date: date
    end_date: date


class HandoverCardOut(ResponseModel):
    child: ChildBriefOut
    assignment: CardPeriodOut
    records: list[CardRecordOut]
    share_texts: list[str]


class NoteCreateRequest(RequestModel):
    body: NoteBody | None = None
    share_text: ShareText | None = None

    @model_validator(mode="after")
    def at_least_one(self) -> NoteCreateRequest:
        if not (self.body or self.share_text):
            raise ValueError("원문이나 공유 문구 중 하나 이상 적어 주세요.")
        return self


class NoteSummaryOut(ResponseModel):
    id: int
    share_text: str | None
    has_body: bool
    author: AuthorOut
    created_at: datetime


class NoteDetailOut(NoteSummaryOut):
    body: str | None
