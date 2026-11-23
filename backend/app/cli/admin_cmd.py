"""Admin commands: add a center with a director invite, export the OpenAPI schema."""

from __future__ import annotations

import argparse
import json
import secrets
from datetime import timedelta

from sqlalchemy import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.cli.common import (
    out,
    owner_engine,
    resolve_output_path,
    setup_cli_logging,
    write_private_file,
)
from app.clock import Clock
from app.config import AppSecrets, Settings, get_settings, load_secrets
from app.main import create_app
from app.models import Center, Invite, Role
from app.security.crypto import NoteKeyring
from app.security.tokens import new_invite_code
from app.services.auth_service import invite_digest


def add_center_command() -> None:
    parser = argparse.ArgumentParser(description="Add a center and issue a director invite.")
    parser.add_argument("name", help="center name (max 50 chars)")
    args = parser.parse_args()
    setup_cli_logging()
    name = args.name.strip()
    if not 1 <= len(name) <= 50:
        raise SystemExit("center name must be 1-50 characters")

    settings = get_settings()
    app_secrets = load_secrets(settings)
    clock = Clock()
    code = new_invite_code()
    engine = owner_engine()
    with Session(engine) as db:
        center = Center(name=name, created_at=clock.now())
        db.add(center)
        db.flush()
        invite = Invite(
            code_hash=invite_digest(app_secrets.session_key, code),
            center_id=center.id,
            role=Role.DIRECTOR.value,
            created_by=None,
            created_at=clock.now(),
            expires_at=clock.now() + timedelta(hours=settings.invite_valid_hours),
        )
        db.add(invite)
        db.flush()
        center_id, invite_id = center.id, invite.id
        # The code never goes to stdout (kept in the container log): only to a 0600
        # file, written before the commit so a failed write leaves no center behind.
        code_file = settings.invite_code_dir.resolve() / f"director_invite_center{center_id}.txt"
        write_private_file(code_file, code)
        try:
            db.commit()
        except SQLAlchemyError:
            code_file.unlink(missing_ok=True)
            raise
    engine.dispose()
    out(
        f"Center id={center_id} created; director invite id={invite_id} issued "
        f"(valid {settings.invite_valid_hours}h). Code written to {code_file} (mode 0600): "
        "hand it over in person, then delete the file."
    )


def export_openapi_command() -> None:
    parser = argparse.ArgumentParser(description="Write the OpenAPI schema as JSON.")
    parser.add_argument("--output", default="../docs/api/openapi.json")
    args = parser.parse_args()
    setup_cli_logging()

    # The schema needs no real secrets or database: use throwaway values.
    ephemeral = AppSecrets(
        database_url=URL.create("postgresql+psycopg", database="unused").render_as_string(),
        session_key=secrets.token_bytes(32),
        keyring=NoteKeyring(active_id="k1", keys={"k1": secrets.token_bytes(32)}),
    )
    app = create_app(Settings(env="development"), ephemeral)
    output = resolve_output_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    out(f"OpenAPI schema written to {output}")
