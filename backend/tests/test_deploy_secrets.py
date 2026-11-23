"""Docker secret files: readable by the containers' group, never by others on the host."""

from __future__ import annotations

import stat
import sys
from pathlib import Path

import pytest
from app.cli import common
from app.cli.common import write_private_file
from app.cli.secrets_cmd import dev_secrets_command

SECRET_NAMES = {
    "session_key",
    "note_keyring",
    "pg_admin_password",
    "owner_password",
    "app_password",
    "owner_database_url",
    "database_url",
}


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def _run_dev_secrets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *extra: str) -> Path:
    monkeypatch.setattr(common, "PROJECT_ROOT", tmp_path)
    monkeypatch.chdir(tmp_path)
    argv = ["ieogagi-dev-secrets", "--dir", "deploy/secrets", "--db-host", "db", *extra]
    monkeypatch.setattr(sys, "argv", argv)
    dev_secrets_command()
    return tmp_path / "deploy" / "secrets"


def test_docker_secrets_are_group_readable_inside_a_private_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret_dir = _run_dev_secrets(tmp_path, monkeypatch, "--group-readable")
    assert _mode(secret_dir) == 0o700  # other host users cannot even list it
    assert {p.name: _mode(p) for p in secret_dir.iterdir()} == dict.fromkeys(SECRET_NAMES, 0o640)


def test_local_secrets_stay_owner_only_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    secret_dir = _run_dev_secrets(tmp_path, monkeypatch)
    assert {p.name: _mode(p) for p in secret_dir.iterdir()} == dict.fromkeys(SECRET_NAMES, 0o600)


def test_group_readable_tightens_an_existing_open_directory(tmp_path: Path) -> None:
    """A pre-existing 0755 directory would let other host users reach the 0640 files."""
    secret_dir = tmp_path / "secrets"
    secret_dir.mkdir()
    secret_dir.chmod(0o755)
    write_private_file(secret_dir / "session_key", "k", group_readable=True)
    assert _mode(secret_dir) == 0o700
    assert _mode(secret_dir / "session_key") == 0o640
