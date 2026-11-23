"""Random tokens and keyed hashing for session tokens and invite codes.

Tokens come from ``secrets`` (CSPRNG). Only a keyed HMAC-SHA256 of a token is
stored, so a database leak alone does not reveal usable session tokens or
invite codes, and the server key acts as a secret salt (pepper).
"""

from __future__ import annotations

import hmac
import secrets

SESSION_TOKEN_BYTES = 32
INVITE_CODE_BYTES = 16


def new_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def new_invite_code() -> str:
    return secrets.token_urlsafe(INVITE_CODE_BYTES)


def keyed_digest(key: bytes, token: str, *, purpose: str) -> str:
    """HMAC-SHA256 over ``purpose:token``; ``purpose`` separates token kinds."""
    message = f"{purpose}:{token}".encode()
    return hmac.digest(key, message, "sha256").hex()
