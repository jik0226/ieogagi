"""Log masking: nested extra fields, bounded depth, and non-production tracebacks."""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

import pytest
from app.db import build_engine
from app.logging_setup import MASK, MAX_MASK_DEPTH, MaskingJsonFormatter
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests.conftest import TEST_DB_URL


def _format(*, include_traceback: bool, exc_info: Any = None, **extra: Any) -> dict[str, Any]:
    record = logging.LogRecord(
        "ieogagi.test", logging.ERROR, __file__, 1, "unhandled_error", None, exc_info
    )
    for key, value in extra.items():
        setattr(record, key, value)
    formatter = MaskingJsonFormatter(include_traceback=include_traceback)
    return json.loads(formatter.format(record))


def _raised(error: Exception) -> tuple:
    with pytest.raises(type(error)) as caught:
        raise error
    return (caught.type, caught.value, caught.tb)


def test_nested_values_in_an_allowed_field_are_masked() -> None:
    reason = {
        "password": "p-value",
        "items": [{"token": "t-value"}, "password=inline-value", ("ok", {"session_id": 7})],
        "count": 3,
    }
    payload = _format(include_traceback=False, reason=reason)
    assert payload["reason"] == {
        "password": MASK,
        "items": [{"token": MASK}, f"password={MASK}", ["ok", {"session_id": MASK}]],
        "count": 3,
    }


def test_masking_depth_is_bounded() -> None:
    deep: Any = "password=deep-value"
    for _ in range(50):
        deep = [deep]
    cycle: list[Any] = []
    cycle.append(cycle)  # would recurse forever without the bound
    payload = _format(include_traceback=False, reason=deep, result=cycle)
    level = payload["reason"]
    for _ in range(MAX_MASK_DEPTH):
        level = level[0]
    assert level == MASK
    assert "deep-value" not in json.dumps(payload)


def test_traceback_is_masked_outside_production() -> None:
    exc_info = _raised(ValueError("login failed password=secret123"))
    traceback = _format(include_traceback=True, exc_info=exc_info)["traceback"]
    assert "secret123" not in traceback
    assert f"password={MASK}" in traceback


def test_sqlalchemy_parameters_in_a_traceback_are_masked() -> None:
    params = {"x": "v", "ids": [1, 2], "did": "bound-value"}  # "]" inside the values too
    error = IntegrityError("INSERT INTO record (did) VALUES (%(did)s)", params, ValueError("dup"))
    traceback = _format(include_traceback=True, exc_info=_raised(error))["traceback"]
    assert f"[parameters: {MASK}]" in traceback
    assert "'v'" not in traceback and "bound-value" not in traceback
    assert "[SQL: INSERT INTO record" in traceback  # the statement stays for debugging


def test_production_logs_only_the_error_type() -> None:
    exc_info = _raised(ValueError("login failed password=secret123"))
    payload = _format(include_traceback=False, exc_info=exc_info, error_type="ValueError")
    assert "traceback" not in payload
    assert payload["error_type"] == "ValueError"
    assert "secret123" not in json.dumps(payload)


def test_engine_keeps_bound_values_out_of_error_messages() -> None:
    """SQLAlchemy does not append the bound values to the message (source-side guard).

    The database's own error text may still quote a value it could not parse, which
    is why production logs carry only the error type.
    """
    engine = build_engine(TEST_DB_URL)
    try:
        with engine.connect() as conn, pytest.raises(DBAPIError) as caught:
            conn.execute(text("SELECT :tag, 1 / 0"), {"tag": "input-value-123"})
    finally:
        engine.dispose()
    assert "input-value-123" not in str(caught.value)
    assert "hide_parameters" in str(caught.value)


def test_sets_and_spaced_values_are_masked() -> None:
    payload = _format(
        include_traceback=False,
        reason={"tags": {"x"}, "frozen": frozenset({"password=two words"}), "token": {"t"}},
    )
    text_out = json.dumps(payload)
    assert "two words" not in text_out and "words" not in text_out
    assert payload["reason"]["token"] == MASK
    assert payload["reason"]["tags"] == ["x"]


def test_other_types_are_logged_as_masked_text() -> None:
    payload = _format(include_traceback=False, reason={"when": date(2026, 10, 17)})
    assert payload["reason"]["when"] == "2026-10-17"
