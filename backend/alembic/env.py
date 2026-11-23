"""Alembic environment.

Migrations run as the schema owner role. The URL comes from a secret file
(``IEOGAGI_OWNER_DATABASE_URL_FILE``) or, in tests, from a connection passed
in ``config.attributes["connection"]``. It is never written in alembic.ini.
"""

from __future__ import annotations

from alembic import context
from app.config import get_settings
from app.models import Base
from sqlalchemy import Connection, create_engine, pool

config = context.config
target_metadata = Base.metadata


def _owner_url() -> str:
    return get_settings().owner_database_url_file.read_text(encoding="utf-8").strip()


def _run(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        _run(connection)
        return
    engine = create_engine(_owner_url(), poolclass=pool.NullPool)
    with engine.connect() as conn:
        _run(conn)
    engine.dispose()


run_migrations_online()
