"""Structured JSON logging with masking of sensitive fields.

Log lines are JSON objects. Only whitelisted ``extra`` fields are emitted,
and any field whose name looks sensitive is replaced with ``***`` before
formatting, so passwords, tokens, invite codes, cookies and note bodies can
never be written to logs by mistake. Masking reaches into nested dicts and
lists, and tracebacks (written outside production only) go through the same
text masking, with SQLAlchemy's bound ``[parameters: ...]`` replaced whole.
Children are referenced by internal id.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

SENSITIVE_KEY = re.compile(
    r"(pass(word)?|secret|token|cookie|session|code|authorization|body|key|alias)", re.IGNORECASE
)
# "password=x", "token: x", and the quoted-key form of reprs/JSON ('password': 'x').
# The value runs to the next comma, semicolon, "&" or line end, so a value with spaces
# ("password=two words") is masked whole; over-masking the rest of a line is acceptable.
SENSITIVE_INLINE = re.compile(
    r"(?i)\b(password|token|code|cookie|secret)\b[\"']?\s*[=:]\s*[^\n,;&]+"
)
# SQLAlchemy puts the bound values on one line: "[parameters: {...}]". The values
# may contain "]", so everything up to the end of that line is replaced.
SQL_PARAMETERS = re.compile(r"\[parameters: [^\n]*")
ALLOWED_EXTRA = (
    "event",
    "request_id",
    "method",
    "route",
    "status",
    "duration_ms",
    "user_id",
    "center_id",
    "target_type",
    "target_id",
    "action",
    "result",
    "reason",
    "error_type",
)
MASK = "***"
MAX_MASK_DEPTH = 5  # nested containers deeper than this are replaced whole


def mask_text(text: str) -> str:
    text = SQL_PARAMETERS.sub(f"[parameters: {MASK}]", text)
    return SENSITIVE_INLINE.sub(lambda m: f"{m.group(1)}={MASK}", text)


def mask_value(key: str, value: Any, depth: int = 0) -> Any:
    """Mask a log field: sensitive keys at any nesting level, secrets inside strings."""
    if SENSITIVE_KEY.search(key):
        return MASK
    if isinstance(value, str):
        return mask_text(value)
    if not isinstance(value, dict | list | tuple | set | frozenset):
        return value
    if depth >= MAX_MASK_DEPTH:
        return MASK
    if isinstance(value, dict):
        return {k: mask_value(str(k), v, depth + 1) for k, v in value.items()}
    return [mask_value(key, item, depth + 1) for item in value]


class MaskingJsonFormatter(logging.Formatter):
    def __init__(self, *, include_traceback: bool) -> None:
        super().__init__()
        self.include_traceback = include_traceback

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": mask_value("message", record.getMessage()),
        }
        for key in ALLOWED_EXTRA:
            if hasattr(record, key):
                payload[key] = mask_value(key, getattr(record, key))
        if record.exc_info and record.exc_info[0] is not None:
            # In production only the exception type is logged: exception
            # messages may contain user input. Tracebacks are for local dev.
            payload["error_type"] = record.exc_info[0].__name__
            if self.include_traceback:
                payload["traceback"] = mask_text(self.formatException(record.exc_info))
        # Any other type (datetime, UUID, ...) is logged as masked text instead of
        # failing the whole line.
        return json.dumps(payload, ensure_ascii=False, default=lambda obj: mask_text(str(obj)))


def configure_logging(level: str, *, include_traceback: bool) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(MaskingJsonFormatter(include_traceback=include_traceback))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for noisy in ("uvicorn.access",):
        logging.getLogger(noisy).disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
