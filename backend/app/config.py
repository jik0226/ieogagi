"""Application settings.

Non-secret settings come from environment variables (prefix ``IEOGAGI_``).
Secret values (DB URL with password, HMAC key, note encryption keyring) are
never read from env vars or code: only from files whose *paths* are configured,
so they can be mounted as Docker secrets and kept out of the repository.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.errors import ConfigurationError
from app.security.crypto import NoteKeyring

MIN_SESSION_KEY_BYTES = 32
KEY_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,20}")  # fits staff_note.key_id


class Settings(BaseSettings):
    """Runtime configuration. Defaults are the safest (production) values."""

    model_config = SettingsConfigDict(env_prefix="IEOGAGI_", env_file=".env", extra="ignore")

    env: Literal["development", "test", "production"] = "production"
    database_url_file: Path = Path("/run/secrets/database_url")
    session_key_file: Path = Path("/run/secrets/session_key")
    note_keyring_file: Path = Path("/run/secrets/note_keyring")
    owner_database_url_file: Path = Path("/run/secrets/owner_database_url")
    allowed_origins: list[str] = Field(default_factory=list)
    cookie_name: str = "__Host-ieogagi_session"
    session_idle_minutes: int = Field(default=10, ge=1, le=60)
    session_absolute_hours: int = Field(default=8, ge=1, le=24)
    invite_valid_hours: int = Field(default=72, ge=1, le=168)
    # Where ieogagi-add-center writes the one-time director invite code (0600 file).
    invite_code_dir: Path = Path(".secrets")
    login_max_failures: int = Field(default=5, ge=3, le=10)
    login_lock_minutes: int = Field(default=15, ge=5, le=120)
    rate_limit_enabled: bool = True
    log_level: Literal["INFO", "WARNING", "ERROR"] = "INFO"

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@dataclass(frozen=True)
class AppSecrets:
    """Secret material loaded once at startup."""

    # repr=False: an accidental log of this object must not print secret values.
    database_url: str = field(repr=False)
    session_key: bytes = field(repr=False)
    keyring: NoteKeyring = field(repr=False)


def _read_secret_text(path: Path, label: str) -> str:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise ConfigurationError(f"secret file for {label} is missing") from exc
    except PermissionError as exc:
        raise ConfigurationError(f"secret file for {label} is not readable") from exc
    if not value:
        raise ConfigurationError(f"secret file for {label} is empty")
    return value


def _decode_b64(value: str, label: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ConfigurationError(f"{label} must be base64 encoded") from exc


def parse_keyring(raw: str) -> NoteKeyring:
    """Parse ``{"active": "k1", "keys": {"k1": "<base64 32 bytes>"}}``."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("note keyring must be JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("keys"), dict):
        raise ConfigurationError("note keyring has an invalid structure")
    keys: dict[str, bytes] = {}
    for key_id, encoded in data["keys"].items():
        if not KEY_ID_PATTERN.fullmatch(str(key_id)):
            raise ConfigurationError("note key ids must be 1-20 letters, digits, '-' or '_'")
        keys[str(key_id)] = _decode_b64(str(encoded), "note key")
    return NoteKeyring(active_id=str(data.get("active", "")), keys=keys)


def load_secrets(settings: Settings) -> AppSecrets:
    """Load and validate all secrets; fail closed on any problem."""
    session_key = _decode_b64(
        _read_secret_text(settings.session_key_file, "session key"), "session key"
    )
    if len(session_key) < MIN_SESSION_KEY_BYTES:
        raise ConfigurationError("session key must be at least 32 bytes")
    keyring = parse_keyring(_read_secret_text(settings.note_keyring_file, "note keyring"))
    database_url = _read_secret_text(settings.database_url_file, "database url")
    return AppSecrets(database_url=database_url, session_key=session_key, keyring=keyring)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
