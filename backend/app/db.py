"""Database engine and per-request session.

All queries go through SQLAlchemy with bound parameters. The session is
opened per request in a context manager, so it is always closed (and any
uncommitted transaction rolled back) even when the request fails.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def build_engine(database_url: str) -> Engine:
    # pool_timeout bounds how long a request can wait for a connection (no long stalls).
    # hide_parameters keeps bound values (user input) out of SQLAlchemy error messages,
    # so they cannot reach a log line or traceback in the first place.
    return create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        pool_timeout=5,
        hide_parameters=True,
    )


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


def get_db(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as db:
        yield db


DbSession = Annotated[Session, Depends(get_db)]
