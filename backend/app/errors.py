"""Application error types.

Every error that reaches a client is an ``AppError`` subclass with a fixed,
generic, user-facing Korean message. Internal details (exception text, SQL,
stack traces) are never put into these objects, so they cannot leak into
responses. Handlers live in ``app.error_handlers``.
"""

from __future__ import annotations

from typing import Any, ClassVar


class ConfigurationError(RuntimeError):
    """Raised at startup when configuration or secrets are invalid (fail closed)."""


class AppError(Exception):
    status_code: ClassVar[int] = 500
    code: ClassVar[str] = "INTERNAL_ERROR"
    default_message: ClassVar[str] = "요청을 처리하지 못했습니다. 잠시 후 다시 시도해 주세요."

    def __init__(self, message: str | None = None, **extra: Any) -> None:
        self.message = message or self.default_message
        self.extra = extra
        super().__init__(self.message)

    def to_body(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message, **self.extra}}


class Unauthenticated(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"
    default_message = "로그인이 필요합니다."


class LoginFailed(AppError):
    # Same message for wrong password, unknown account, disabled and locked
    # accounts so the response does not reveal which case happened.
    status_code = 401
    code = "LOGIN_FAILED"
    default_message = "아이디 또는 비밀번호가 올바르지 않거나, 잠시 로그인이 제한된 계정입니다."


class Forbidden(AppError):
    status_code = 403
    code = "FORBIDDEN"
    default_message = "접근 권한이 없습니다."


class NotFound(AppError):
    status_code = 404
    code = "NOT_FOUND"
    default_message = "대상을 찾을 수 없습니다."


class Conflict(AppError):
    status_code = 409
    code = "CONFLICT"
    default_message = "요청이 현재 상태와 맞지 않습니다."


class InvalidRequest(AppError):
    status_code = 422
    code = "VALIDATION_FAILED"
    default_message = "입력값을 확인해 주세요."


class SensitiveConfirmRequired(AppError):
    status_code = 422
    code = "SENSITIVE_CONFIRM_REQUIRED"
    default_message = "건강·가정 관련 내용이 있는 것 같습니다. 학습 내용만 적었는지 확인해 주세요."


class SensitiveBasisRequired(AppError):
    status_code = 422
    code = "SENSITIVE_BASIS_REQUIRED"
    default_message = "민감정보 동의 또는 법령상 근거를 먼저 확인해야 원문을 입력할 수 있습니다."


class PayloadTooLarge(AppError):
    status_code = 413
    code = "REQUEST_TOO_LARGE"
    default_message = "요청 내용이 너무 큽니다."


class RateLimited(AppError):
    status_code = 429
    code = "RATE_LIMITED"
    default_message = "요청이 너무 많습니다. 잠시 후 다시 시도해 주세요."


class InternalError(AppError):
    """Generic 500 used by the catch-all handler."""
