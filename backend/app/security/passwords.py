"""Password hashing (argon2id with per-hash random salt) and password policy."""

from __future__ import annotations

import logging
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 128  # bounds hashing cost per request
MIN_CHARACTER_CLASSES = 2

logger = logging.getLogger(__name__)

_hasher = PasswordHasher()  # argon2id, library-recommended parameters, random salt per hash
# Hash of a random value used to spend equal time when the account does not
# exist, so response timing does not reveal which login ids are registered.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except (VerificationError, InvalidHashError):
        # A stored hash that cannot be parsed is a data problem: deny and record it.
        logger.warning("password_hash_unverifiable")
        return False


def spend_equal_time(password: str) -> None:
    """Run a verification against a dummy hash and discard the result."""
    verify_password(_DUMMY_HASH, password)


def needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def password_policy_violation(password: str) -> str | None:
    """Return a Korean reason if the password violates policy, else None."""
    if len(password) < MIN_PASSWORD_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
        return "비밀번호는 10자 이상 128자 이하여야 합니다."
    classes = [
        any(ch.islower() for ch in password),
        any(ch.isupper() for ch in password),
        any(ch.isdigit() for ch in password),
        any(not ch.isalnum() for ch in password),
    ]
    if sum(classes) < MIN_CHARACTER_CLASSES:
        return "비밀번호는 영문 대문자·소문자·숫자·특수문자 중 2종류 이상을 섞어야 합니다."
    return None
