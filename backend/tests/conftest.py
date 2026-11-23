"""Test fixtures.

Tests run against a real PostgreSQL database (``IEOGAGI_TEST_DATABASE_URL``,
a superuser URL to a disposable database). The schema is built with the real
Alembic migrations as the owner role, and the app connects with
``SET ROLE ieogagi_app`` so tests exercise the production grants (e.g. the
audit log being INSERT/SELECT-only).
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from app.config import AppSecrets, Settings
from app.db import build_session_factory
from app.main import create_app
from app.security.crypto import NoteKeyring
from app.security.ratelimit import limiter
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from tests.factories import Factory
from tests.fixed_clock import FixedClock

TEST_DB_URL = os.environ.get("IEOGAGI_TEST_DATABASE_URL", "postgresql+psycopg:///ieogagi_test")
BACKEND_DIR = Path(__file__).resolve().parent.parent
ORIGIN = "https://testserver"
TRUNCATE_ALL = (
    "TRUNCATE audit_log, staff_note, record, assignment, child, invite, user_session, "
    "app_user, center RESTART IDENTITY CASCADE"
)
SET_ROLE = {"ieogagi_owner": "SET ROLE ieogagi_owner", "ieogagi_app": "SET ROLE ieogagi_app"}
ROLE_SETUP = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ieogagi_owner') THEN
    CREATE ROLE ieogagi_owner NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ieogagi_app') THEN
    CREATE ROLE ieogagi_app NOLOGIN;
  END IF;
END $$;
"""


def _role_engine(role: str) -> Engine:
    engine = create_engine(TEST_DB_URL)

    @event.listens_for(engine, "connect")
    def _set_role(dbapi_connection, _record) -> None:
        with dbapi_connection.cursor() as cursor:
            cursor.execute(SET_ROLE[role])
        dbapi_connection.commit()

    return engine


@pytest.fixture(scope="session")
def admin_engine() -> Iterator[Engine]:
    engine = create_engine(TEST_DB_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conn.execute(text(ROLE_SETUP))
        # Same layout as production: the owner role owns the schema (and so can grant).
        conn.execute(text("CREATE SCHEMA public AUTHORIZATION ieogagi_owner"))
        # Production: the owner role owns the database and may create this trusted
        # extension itself; the test database is not owned by it, so do it here.
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS btree_gist SCHEMA public"))
    owner = _role_engine("ieogagi_owner")
    with owner.begin() as conn:
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        config.attributes["connection"] = conn
        command.upgrade(config, "head")
    owner.dispose()
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def app_engine(admin_engine: Engine) -> Iterator[Engine]:
    engine = _role_engine("ieogagi_app")
    yield engine
    engine.dispose()


@pytest.fixture
def db(admin_engine: Engine) -> Iterator[Session]:
    """Admin session for arranging data and asserting on raw rows."""
    with admin_engine.begin() as conn:
        conn.execute(text(TRUNCATE_ALL))
    factory = sessionmaker(bind=admin_engine, expire_on_commit=False)
    with factory() as session:
        yield session


@pytest.fixture
def clock() -> FixedClock:
    # 2026-10-20 10:00 KST, inside the default mentor assignment of the factories.
    return FixedClock(datetime(2026, 10, 20, 1, 0, tzinfo=UTC))


@pytest.fixture
def app_secrets() -> AppSecrets:
    return AppSecrets(
        database_url=TEST_DB_URL,
        session_key=secrets.token_bytes(32),
        keyring=NoteKeyring(active_id="k1", keys={"k1": secrets.token_bytes(32)}),
    )


@pytest.fixture
def settings() -> Settings:
    return Settings(env="test", allowed_origins=[ORIGIN], rate_limit_enabled=False)


@pytest.fixture
def app(settings: Settings, app_secrets: AppSecrets, clock: FixedClock, app_engine: Engine, db):
    application = create_app(settings, app_secrets, clock)
    application.state.engine.dispose()
    application.state.engine = app_engine
    application.state.session_factory = build_session_factory(app_engine)
    limiter.reset()
    return application


@pytest.fixture
def make_client(app) -> Callable[..., TestClient]:
    clients: list[TestClient] = []

    def _make(*, raise_server_exceptions: bool = True) -> TestClient:
        client = TestClient(
            app,
            base_url=ORIGIN,
            headers={"Origin": ORIGIN},
            raise_server_exceptions=raise_server_exceptions,
        )
        clients.append(client)
        return client

    yield _make
    for client in clients:
        client.close()


@pytest.fixture
def factory(db: Session, app, app_secrets: AppSecrets, clock: FixedClock, make_client) -> Factory:
    return Factory(
        db=db,
        settings=app.state.settings,
        secrets=app_secrets,
        clock=clock,
        make_client=make_client,
    )
