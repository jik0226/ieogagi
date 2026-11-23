"""Regression tests for the 2026-10-13 external security review findings."""

from __future__ import annotations

import logging
import os
import stat
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import pytest
from app.cli import admin_cmd, common
from app.cli.common import write_private_file
from app.config import AppSecrets, Settings
from app.models import Invite, Record
from app.services.auth_service import invite_digest
from sqlalchemy import select, text

from tests.conftest import _role_engine
from tests.factories import Factory
from tests.scenario import World, build_world

PENDING_HIDE = (
    "UPDATE record SET hidden_at = now(), hidden_by = :staff, "
    "hidden_reason_code = 'SENSITIVE' WHERE id = :id"
)


@pytest.fixture
def world(factory: Factory) -> World:
    return build_world(factory)


def test_correction_waits_for_a_pending_hide(app_engine, factory: Factory, world: World) -> None:
    """A hide that commits mid-correction must not leave a visible correction behind."""
    original = factory.record(world.child, world.mentor_now, date(2026, 10, 13), did="원본")
    mentor = factory.client_for(world.mentor_now)
    body = {"did": "정정본", "stuck": "", "next_step": ""}
    # The pool is entered first so it exits last: the held lock is released
    # before the pool waits for the request thread, even when an assert fails.
    with ThreadPoolExecutor(max_workers=1) as pool, app_engine.connect() as conn:
        conn.execute(text(PENDING_HIDE), {"staff": world.staff_a.id, "id": original.id})
        pending = pool.submit(mentor.post, f"/api/records/{original.id}/corrections", json=body)
        time.sleep(0.5)
        assert not pending.done(), "correction must wait for the record row lock"
        conn.commit()
        response = pending.result(timeout=10)
    assert response.status_code == 403
    successors = factory.db.scalars(select(Record.id).where(Record.corrects_id == original.id))
    assert list(successors) == []


def test_hide_waits_for_a_pending_correction(app_engine, factory: Factory, world: World) -> None:
    """Hide takes the same record lock first, so it runs after the correction ends."""
    original = factory.record(world.child, world.mentor_now, date(2026, 10, 13), did="원본")
    staff = factory.client_for(world.staff_a)
    with ThreadPoolExecutor(max_workers=1) as pool, app_engine.connect() as conn:
        conn.execute(text("SELECT id FROM record WHERE id = :id FOR UPDATE"), {"id": original.id})
        pending = pool.submit(
            staff.post, f"/api/records/{original.id}/hide", json={"reason_code": "SENSITIVE"}
        )
        time.sleep(0.5)
        assert not pending.done(), "hide must wait for the record row lock"
        conn.rollback()
        response = pending.result(timeout=10)
    assert response.status_code == 200
    assert response.json()["hidden_reason_code"] == "SENSITIVE"


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def test_private_file_never_exists_with_loose_permissions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Secrets are 0600 before they appear under their name, and replace old files whole."""
    secret_dir = tmp_path / "secrets"
    loose = secret_dir / "loose"
    secret_dir.mkdir(mode=0o700)
    loose.write_text("old")
    loose.chmod(0o644)
    old_inode = loose.stat().st_ino
    victim = tmp_path / "victim"
    victim.write_text("keep")
    (secret_dir / "link").symlink_to(victim)
    modes_at_rename: list[int] = []
    real_replace = os.replace

    def spy_replace(src: str | Path, dst: str | Path) -> None:
        modes_at_rename.append(_mode(Path(src)))
        real_replace(src, dst)

    monkeypatch.setattr(common.os, "replace", spy_replace)
    previous_umask = os.umask(0)
    try:
        for name in ("new", "loose", "link"):
            write_private_file(secret_dir / name, f"{name} secret")
    finally:
        os.umask(previous_umask)
    assert modes_at_rename == [0o600, 0o600, 0o600]
    assert {path.name: _mode(path) for path in secret_dir.iterdir()} == {
        "new": 0o600,
        "loose": 0o600,
        "link": 0o600,
    }
    assert loose.stat().st_ino != old_inode  # replaced, not rewritten in place
    assert victim.read_text() == "keep"  # a symlink at the target is replaced, not followed


def test_private_file_refuses_a_directory_others_can_write(tmp_path: Path) -> None:
    shared = tmp_path / "shared"
    shared.mkdir()
    shared.chmod(0o777)
    with pytest.raises(SystemExit):
        write_private_file(shared / "key", "secret")
    assert list(shared.iterdir()) == []


def test_add_center_logs_ids_but_never_the_invite_code(
    factory: Factory,
    settings: Settings,
    app_secrets: AppSecrets,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The one-time code goes to a 0600 file only; stdout (the container log) has ids."""
    code_dir = tmp_path / "invites"
    owner = _role_engine("ieogagi_owner")
    monkeypatch.setattr(sys, "argv", ["ieogagi-add-center", "새싹지역아동센터"])
    monkeypatch.setattr(admin_cmd, "owner_engine", lambda: owner)
    monkeypatch.setattr(
        admin_cmd, "get_settings", lambda: settings.model_copy(update={"invite_code_dir": code_dir})
    )
    monkeypatch.setattr(admin_cmd, "load_secrets", lambda _settings: app_secrets)
    try:
        with caplog.at_level(logging.INFO, logger="ieogagi.cli"):
            admin_cmd.add_center_command()
    finally:
        owner.dispose()
    (code_file,) = code_dir.iterdir()
    code = code_file.read_text(encoding="utf-8").strip()
    digest = invite_digest(app_secrets.session_key, code)
    invite = factory.db.scalar(select(Invite).where(Invite.code_hash == digest))
    assert invite is not None
    assert _mode(code_file) == 0o600
    logged = caplog.text + capsys.readouterr().out
    assert code not in logged
    assert f"director invite id={invite.id} issued" in logged
