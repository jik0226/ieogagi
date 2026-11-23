"""``ieogagi-db-roles``: create the owner/app roles and the database.

Runs with a PostgreSQL administrator connection (``IEOGAGI_ADMIN_DATABASE_URL``,
default: local socket as the current OS user). Role passwords come from the
secret files; identifiers and literals are composed with ``psycopg.sql`` so
nothing is concatenated into SQL text.
"""

from __future__ import annotations

import argparse
import os

import psycopg
from psycopg import sql

from app.cli.common import out, read_secret, resolve_output_path, setup_cli_logging

ROLES = (("ieogagi_owner", "owner_password"), ("ieogagi_app", "app_password"))


def _ensure_role(conn: psycopg.Connection, role: str, password: str) -> None:
    exists = conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
    verb = sql.SQL("ALTER ROLE ") if exists else sql.SQL("CREATE ROLE ")
    conn.execute(
        sql.Composed(
            [verb, sql.Identifier(role), sql.SQL(" LOGIN PASSWORD "), sql.Literal(password)]
        )
    )


def db_roles_command() -> None:
    parser = argparse.ArgumentParser(description="Create database roles and database.")
    parser.add_argument("--secrets-dir", default=".secrets")
    parser.add_argument("--db-name", default="ieogagi")
    args = parser.parse_args()
    setup_cli_logging()

    admin_url = os.environ.get("IEOGAGI_ADMIN_DATABASE_URL", "dbname=postgres")
    secrets_dir = resolve_output_path(args.secrets_dir)
    with psycopg.connect(admin_url, autocommit=True) as conn:
        for role, secret_name in ROLES:
            _ensure_role(conn, role, read_secret(secrets_dir / secret_name))
        db_exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (args.db_name,)
        ).fetchone()
        database = sql.Identifier(args.db_name)
        if not db_exists:
            conn.execute(
                sql.Composed(
                    [sql.SQL("CREATE DATABASE "), database, sql.SQL(" OWNER ieogagi_owner")]
                )
            )
        conn.execute(
            sql.Composed(
                [sql.SQL("REVOKE CONNECT ON DATABASE "), database, sql.SQL(" FROM PUBLIC")]
            )
        )
        conn.execute(
            sql.Composed(
                [
                    sql.SQL("GRANT CONNECT ON DATABASE "),
                    database,
                    sql.SQL(" TO ieogagi_owner, ieogagi_app"),
                ]
            )
        )
    out(f"Roles ready and database '{args.db_name}' owned by ieogagi_owner.")
