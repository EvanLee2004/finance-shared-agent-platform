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
        # No env → skip
        monkeypatch.delenv("FSA_BOOTSTRAP_ADMIN_USER", raising=False)
        monkeypatch.delenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", raising=False)
        assert bootstrap_admin_if_needed(conn) is None
        assert count_admins(conn) == 0

        monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "seedadmin")
        monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "seed-pass-99")
        first = bootstrap_admin_if_needed(conn)
        conn.commit()
        assert first is not None
        assert count_admins(conn) == 1
        user = get_user_by_username(conn, "seedadmin")
        assert user is not None
        assert user.role == "admin"

        # Second call must not create another admin
        second = bootstrap_admin_if_needed(conn)
        assert second is None
        assert count_admins(conn) == 1
    finally:
        conn.close()


def test_bootstrap_via_app_lifespan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """App lifespan bootstrap only when no admin — drive real app entry."""
    from fastapi.testclient import TestClient

    root = tmp_path / "data"
    root.mkdir()
    monkeypatch.setenv("FSA_DATA_ROOT", str(root))
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "bootadmin")
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "boot-pass-123")
    monkeypatch.setenv("FSA_OPENCODE_BASE_URL", "http://127.0.0.1:1")

    # Fresh import path: TestClient runs lifespan migrate + bootstrap
    from app.main import app

    with TestClient(app) as c:
        r = c.post(
            "/api/v1/auth/login",
            json={"username": "bootadmin", "password": "boot-pass-123"},
        )
        assert r.status_code == 200, r.text
        assert "fsa_sid" in r.cookies

    # Re-open with same DB: bootstrap must not block re-login
    with TestClient(app) as c2:
        r2 = c2.post(
            "/api/v1/auth/login",
            json={"username": "bootadmin", "password": "boot-pass-123"},
        )
        assert r2.status_code == 200
    conn = connect(root / "app.db")
    try:
        from app.services.auth_service import count_admins

        assert count_admins(conn) == 1
    finally:
        conn.close()
