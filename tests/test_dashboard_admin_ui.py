"""W10: dashboard stats + admin audit/grant product surface."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_dashboard_stats_after_login(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills = tmp_path / "sk"
    skills.mkdir()
    (skills / "catalog.yaml").write_text(
        "skills:\n  - id: s1\n    version: \"1.0\"\n    summary: t\n    path: skills/s1\n",
        encoding="utf-8",
    )
    (skills / "skills" / "s1").mkdir(parents=True)
    (skills / "skills" / "s1" / "SKILL.md").write_text("#\n", encoding="utf-8")
    monkeypatch.setenv("FSA_SKILLS_ROOT", str(skills))
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-123")
    monkeypatch.setenv("FSA_OPENCODE_BASE_URL", "http://127.0.0.1:1")
    from app.main import app

    with TestClient(app) as c:
        assert c.get("/api/v1/dashboard/stats").status_code == 401
        assert (
            c.post(
                "/api/v1/auth/login",
                json={"username": "admin", "password": "admin-pass-123"},
            ).status_code
            == 200
        )
        c.post("/api/v1/admin/skills/sync", json={})
        r = c.get("/api/v1/dashboard/stats")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["skill_total"] >= 1
        assert body["skill_runnable"] >= 1
        assert "chat_count" in body


def test_admin_view_source_has_grant_and_audit_ui() -> None:
    root = Path(__file__).resolve().parents[1]
    admin = (root / "frontend" / "src" / "views" / "AdminView.vue").read_text(
        encoding="utf-8"
    )
    assert "审计" in admin
    assert "putGrant" in admin or "授权" in admin
    assert "fetchAdminAudit" in admin
    router = (root / "frontend" / "src" / "router" / "index.js").read_text(
        encoding="utf-8"
    )
    assert "admin" in router
    assert "AdminView" in router


def test_home_open_chat_passes_id_query_and_chat_selects() -> None:
    """P1-W10-04: recent session click must hand off chat id to ChatView."""
    root = Path(__file__).resolve().parents[1]
    home = (root / "frontend" / "src" / "views" / "HomeView.vue").read_text(
        encoding="utf-8"
    )
    chat = (root / "frontend" / "src" / "views" / "ChatView.vue").read_text(
        encoding="utf-8"
    )
    assert "query:" in home or "query =" in home
    assert "openChat" in home
    assert "route.query.id" in chat or 'route.query.id' in chat
    assert "selectChat" in chat
