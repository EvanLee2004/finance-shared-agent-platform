"""FastAPI dependencies: DB connection and current user."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from typing import Annotated

from fastapi import Cookie, Depends, Request

from app.db.connection import connect, db_path
from app.domain.errors import AppError, AuthRequired
from app.services import auth_service
from app.services.auth_service import COOKIE_NAME, UserRecord


def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = connect(db_path())
    try:
        yield conn
    finally:
        conn.close()


ConnDep = Annotated[sqlite3.Connection, Depends(get_conn)]


def get_current_user(
    conn: ConnDep,
    fsa_sid: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> UserRecord:
    try:
        user, _session = auth_service.resolve_session(conn, fsa_sid)
        return user
    except AuthRequired:
        raise
    except AppError:
        raise
    except Exception as exc:  # pragma: no cover
        raise AuthRequired() from exc


def client_ip(request: Request) -> str | None:
    if request.client:
        return request.client.host
    return None
