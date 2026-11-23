"""Shared helpers for admin commands (console_scripts entry points)."""

from __future__ import annotations

import logging
import os
import sys
import tempfile
from pathlib import Path

from sqlalchemy import Engine, create_engine

from app.config import get_settings

logger = logging.getLogger("ieogagi.cli")

# backend/app/cli/common.py -> repository root. Command output files must stay inside it.
PROJECT_ROOT = Path(__file__).resolve().parents[3]


def setup_cli_logging() -> None:
    """Operator-facing output goes through logging to stdout (no print statements).

    In Docker this stdout is kept in the container log, so ``out()`` must never
    carry a secret value (invite code, password, key). Secrets go to a file
    through ``write_private_file`` and the log names only the event and ids.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)


def out(message: str) -> None:
    logger.info(message)


def resolve_output_path(raw: str) -> Path:
    """Resolve a user-given output path and refuse anything outside the project.

    Blocks ``../../`` style paths and absolute paths pointing elsewhere, so a
    command can only write where the operator expects (경로 조작 방지).
    """
    resolved = (Path.cwd() / raw).resolve()
    if not resolved.is_relative_to(PROJECT_ROOT):
        raise SystemExit(f"output path must be inside the project directory: {PROJECT_ROOT}")
    return resolved


def read_secret(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def owner_engine() -> Engine:
    """Engine for the schema-owner role (admin tasks such as seeding or adding centers)."""
    return create_engine(read_secret(get_settings().owner_database_url_file))


def check_private_dir(directory: Path) -> None:
    """Refuse a directory where someone else could swap or plant secret files."""
    info = directory.stat()
    if info.st_uid != os.getuid() or info.st_mode & 0o022:
        raise SystemExit(
            f"{directory} must be owned by the current user and not writable by group or others"
        )


def write_private_file(path: Path, content: str, *, group_readable: bool = False) -> None:
    """Write a file that only the current user can read, from its first byte.

    ``mkstemp`` creates a new temporary file with mode 0600 (O_EXCL, so never an
    existing file or symlink) next to the target, and one ``os.replace`` swaps it
    in. There is no moment with looser permissions, and a reader sees either the
    old file or the complete new one.

    ``group_readable`` adds group read (0640) before any content is written. Docker
    Compose bind-mounts secret files with their host owner and mode, so containers that
    run as another uid read them through the operator's group (``group_add``). The
    directory stays 0700, so on the host nobody else can reach the files.
    """
    directory = path.parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    check_private_dir(directory)
    if group_readable and directory.stat().st_mode & 0o077:
        # Group-readable files are only private while nobody else can enter the
        # directory, so an existing 0755 directory is tightened to 0700 first.
        directory.chmod(0o700)
    fd, temp_name = tempfile.mkstemp(dir=directory, prefix=f".{path.name}.", suffix=".tmp")
    temp = Path(temp_name)
    try:
        if group_readable:
            os.fchmod(fd, 0o640)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)  # only still there when writing failed
