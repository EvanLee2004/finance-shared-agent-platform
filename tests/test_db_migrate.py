"""G1: migrate applies schema_mvp; version=1; PRAGMAs on."""

from __future__ import annotations

from pathlib import Path

import pytest
from app.db.connection import connect, pragma_snapshot
from app.db.migrate import get_schema_version, migrate


def test_migrate_version_is_1(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    conn = connect(db)
    try:
        version = migrate(conn)
        assert version == 1
        assert get_schema_version(conn) == 1
        # core tables exist
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for expected in (
            "schema_meta",
            "users",
            "auth_sessions",
            "audit_events",
            "skills",
            "chat_sessions",
        ):
            assert expected in tables
    finally:
        conn.close()


def test_pragmas_on_connect(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    conn = connect(db)
    try:
        snap = pragma_snapshot(conn)
        assert snap["foreign_keys"] == 1
        assert snap["journal_mode"] == "WAL"
        assert snap["busy_timeout"] == 5000
    finally:
        conn.close()


def test_migrate_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "app.db"
    conn = connect(db)
    try:
        migrate(conn)
        migrate(conn)
        assert get_schema_version(conn) == 1
    finally:
        conn.close()


def test_bootstrap_admin_only_when_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.services.auth_service import (
        bootstrap_admin_if_needed,
        count_admins,
        get_user_by_username,
    )

    db = tmp_path / "app.db"
    conn = connect(db)
    try:
        migrate(conn)
        monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "seedadmin")
        monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "seed-pass-99")
        first = bootstrap_admin_if_needed(conn)
        conn.commit()
        assert first is not None
        assert count_admins(conn) == 1
        user = get_user_by_username(conn, "seedadmin")
        assert user is not None
        assert user.role == "admin"

        second = bootstrap_admin_if_needed(conn)
        assert second is None
        assert count_admins(conn) == 1
    finally:
        conn.close()
