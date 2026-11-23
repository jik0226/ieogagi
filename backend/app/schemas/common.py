"""Shared constrained types for request validation.

Every request body model forbids unknown fields and every string has an
explicit length bound and, where possible, an allow-list pattern. Integer
ids are bounded so oversized values cannot overflow the BIGINT columns.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import Path
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

MAX_ID = 2**53 - 1  # also the largest integer JavaScript can represent exactly

IdPath = Annotated[int, Path(ge=1, le=MAX_ID)]

# Calendar range the service accepts; also keeps date arithmetic far from overflow.
MIN_DATE = date(2020, 1, 1)
MAX_DATE = date(2100, 12, 31)

LoginId = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{4,32}$")]
PersonName = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=30, pattern=r"^[가-힣A-Za-z0-9 ._-]+$"
    ),
]
ChildAlias = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=20, pattern=r"^[가-힣A-Za-z0-9 ._-]+$"
    ),
]
InviteCode = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{16,64}$")]
# Free text: any characters except control characters (NUL etc.); newline and tab allowed.
NO_CONTROL_CHARS = r"^[^\x00-\x08\x0B\x0C\x0E-\x1F\x7F]*$"
# Passwords are only hashed, but control characters are still refused at the edge (422).
PasswordInput = Annotated[
    str, StringConstraints(min_length=1, max_length=128, pattern=NO_CONTROL_CHARS)
]
RecordText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=500, pattern=NO_CONTROL_CHARS)
]
NoteBody = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=2000, pattern=NO_CONTROL_CHARS)
]
ShareText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=200, pattern=NO_CONTROL_CHARS)
]

Grade = Literal[
    "초1",
    "초2",
    "초3",
    "초4",
    "초5",
    "초6",
    "중1",
    "중2",
    "중3",
    "고1",
    "고2",
    "고3",
]


class RequestModel(BaseModel):
    """Base for request bodies: unknown fields are rejected, not ignored."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)


class ResponseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


IdField = Annotated[int, Field(ge=1, le=MAX_ID)]
DateValue = Annotated[date, Field(ge=MIN_DATE, le=MAX_DATE)]
