"""``ieogagi-dev-secrets``: generate local development secrets into ``.secrets/``.

Everything is random (``secrets`` module) and written with 0600 permissions
into a git-ignored directory. Production secrets are created the same way on
the server and mounted as Docker secrets; none are ever committed. For Docker
(``--group-readable``) the files are 0640 so the containers, which run as other
uids, can read them through the operator's group; the directory stays 0700.
"""

from __future__ import annotations

import argparse
import base64
import json
import secrets

from sqlalchemy import URL

from app.cli.common import out, resolve_output_path, setup_cli_logging, write_private_file

KEY_BYTES = 32


def _b64_key() -> str:
    return base64.b64encode(secrets.token_bytes(KEY_BYTES)).decode()


def _database_url(role: str, password: str, args: argparse.Namespace) -> str:
    url = URL.create(
        "postgresql+psycopg",
        username=role,
        password=password,
        host=args.db_host,
        port=5432,
        database=args.db_name,
    )
    return url.render_as_string(hide_password=False)


def dev_secrets_command() -> None:
    parser = argparse.ArgumentParser(description="Generate local development secrets.")
    parser.add_argument("--dir", default=".secrets", help="output directory (git-ignored)")
    parser.add_argument("--db-name", default="ieogagi")
    parser.add_argument("--db-host", default="localhost")
    parser.add_argument("--force", action="store_true", help="overwrite existing files")
    parser.add_argument(
        "--group-readable",
        action="store_true",
        help="mode 0640 for Docker secrets (containers read them via group_add)",
    )
    args = parser.parse_args()
    setup_cli_logging()

    target = resolve_output_path(args.dir)
    if (target / "session_key").exists() and not args.force:
        out(f"{target} already has secrets; use --force to regenerate.")
        return
    owner_pw = secrets.token_urlsafe(24)
    app_pw = secrets.token_urlsafe(24)
    files = {
        "session_key": _b64_key(),
        "note_keyring": json.dumps({"active": "k1", "keys": {"k1": _b64_key()}}),
        # Only used by the PostgreSQL container's superuser in deploy/; unused locally.
        "pg_admin_password": secrets.token_urlsafe(24),
        "owner_password": owner_pw,
        "app_password": app_pw,
        "owner_database_url": _database_url("ieogagi_owner", owner_pw, args),
        "database_url": _database_url("ieogagi_app", app_pw, args),
    }
    for name, content in files.items():
        write_private_file(target / name, content, group_readable=args.group_readable)
    mode = "0640, directory 0700" if args.group_readable else "0600"
    out(f"Wrote {len(files)} secret files to {target} (mode {mode}).")
