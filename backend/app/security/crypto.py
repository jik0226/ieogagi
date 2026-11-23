"""AES-256-GCM encryption for staff note bodies (health/family details).

- 256-bit keys only, loaded from a secret file outside the database.
- A fresh random 96-bit nonce (``secrets.token_bytes``) for every encryption.
- Associated data binds the ciphertext to its note id and child id, so a
  ciphertext copied into another row fails authentication on decrypt.
- ``key_id`` is stored next to each ciphertext to allow key rotation.
"""

from __future__ import annotations

import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.errors import ConfigurationError

KEY_BYTES = 32
NONCE_BYTES = 12


class NoteDecryptionError(Exception):
    """Ciphertext could not be authenticated (tampered, moved, or wrong key)."""


@dataclass(frozen=True)
class EncryptedNote:
    ciphertext: bytes
    nonce: bytes
    key_id: str


@dataclass(frozen=True)
class NoteKeyring:
    active_id: str
    keys: Mapping[str, bytes] = field(repr=False)

    def __post_init__(self) -> None:
        # Keep a private read-only copy: the caller's dict cannot change our keys.
        object.__setattr__(self, "keys", MappingProxyType(dict(self.keys)))
        if self.active_id not in self.keys:
            raise ConfigurationError("active note key id is not in the keyring")
        for key in self.keys.values():
            if len(key) != KEY_BYTES:
                raise ConfigurationError("note keys must be exactly 256 bits")

    def key_for(self, key_id: str) -> bytes:
        key = self.keys.get(key_id)
        if key is None:
            raise NoteDecryptionError
        return key


def _associated_data(note_id: int, child_id: int) -> bytes:
    return f"ieogagi:staff_note:{note_id}:{child_id}".encode()


def encrypt_note(
    keyring: NoteKeyring, plaintext: str, *, note_id: int, child_id: int
) -> EncryptedNote:
    nonce = secrets.token_bytes(NONCE_BYTES)
    cipher = AESGCM(keyring.key_for(keyring.active_id))
    ciphertext = cipher.encrypt(
        nonce, plaintext.encode("utf-8"), _associated_data(note_id, child_id)
    )
    return EncryptedNote(ciphertext=ciphertext, nonce=nonce, key_id=keyring.active_id)


def decrypt_note(keyring: NoteKeyring, note: EncryptedNote, *, note_id: int, child_id: int) -> str:
    cipher = AESGCM(keyring.key_for(note.key_id))
    try:
        plaintext = cipher.decrypt(note.nonce, note.ciphertext, _associated_data(note_id, child_id))
    except InvalidTag as exc:
        raise NoteDecryptionError from exc
    return plaintext.decode("utf-8")
