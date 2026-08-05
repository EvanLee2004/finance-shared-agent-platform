"""Skills catalog sync, grants (published∩grant), isolation, audit."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.adapters.skills_repo import load_catalog, parse_catalog_yaml
from app.db.connection import connect
from app.db.migrate import migrate
from app.services import auth_service, skill_service


SAMPLE_CATALOG = """
# test catalog
skills:
  - id: demo-alpha
    version: "0.1.0"
    summary: "Alpha skill for tests"
    path: skills/demo-alpha
  - id: demo-beta
    version: "0.2.0"
    summary: "Beta skill for tests"
    path: skills/demo-beta
"""


def _write_skills_tree(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "catalog.yaml").write_text(SAMPLE_CATALOG, encoding="utf-8")
    for key in ("demo-alpha", "demo-beta"):
        d = root / "skills" / key
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(f"# {key}\n", encoding="utf-8")
    return root


def test_parse_catalog_yaml_real_shape() -> None:
    items = parse_catalog_yaml(SAMPLE_CATALOG)
    assert len(items) == 2
    assert items[0]["id"] == "demo-alpha"
    assert items[1]["version"] == "0.2.0"


def test_load_catalog_from_fixture(tmp_path: Path) -> None:
    root = _write_skills_tree(tmp_path / "skills-repo")
    cat = load_catalog(root)
    assert cat["ok"] is True
    assert cat["count"] == 2
    keys = {i["skill_key"] for i in cat["items"]}
    assert keys == {"demo-alpha", "demo-beta"}


def test_sync_grant_runnable_filter(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills_path = _write_skills_tree(tmp_path / "finance-shared-skills")
    monkeypatch.setenv("FSA_SKILLS_ROOT", str(skills_path))
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-123")
    from app.main import app

    with TestClient(app) as c:
        assert c.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-pass-123"},
        ).status_code == 200

        # non-admin cannot sync
        conn = connect(data_root / "app.db")
        migrate(conn)
        auth_service.create_user(
            conn, username="alice", password="alice-pass-1", display_name="Alice"
        )
        conn.commit()
        conn.close()

        sync = c.post("/api/v1/admin/skills/sync", json={"pull": False})
        assert sync.status_code == 200, sync.text
        body = sync.json()
        assert body["ok"] is True
        assert body["upserted"] == 2

        # admin runnable sees all published
        r = c.get("/api/v1/skills?scope=runnable")
        assert r.status_code == 200
        admin_items = r.json()["items"]
        assert len(admin_items) == 2
        assert all(i["runnable"] for i in admin_items)

        skill_id = admin_items[0]["id"]
        skill_key = admin_items[0]["skill_key"]

        # grant only demo-alpha (first) to alice by username → need user id
        conn = connect(data_root / "app.db")
        alice = auth_service.get_user_by_username(conn, "alice")
        assert alice is not None
        conn.close()

        g = c.put(
            "/api/v1/admin/grants",
            json={
                "skill_id": skill_id,
                "principal_type": "user",
                "principal_id": alice.id,
            },
        )
        assert g.status_code == 200, g.text

        # login alice
        c.cookies.clear()
        assert c.post(
            "/api/v1/auth/login",
            json={"username": "alice", "password": "alice-pass-1"},
        ).status_code == 200

        ru = c.get("/api/v1/skills?scope=runnable")
        assert ru.status_code == 200
        keys = {i["skill_key"] for i in ru.json()["items"]}
        assert skill_key in keys
        assert len(keys) == 1  # only granted published skill

        # alice cannot sync
        bad = c.post("/api/v1/admin/skills/sync", json={})
        assert bad.status_code == 403
        assert bad.json()["code"] == "forbidden"

        # alice cannot grant
        bad2 = c.put(
            "/api/v1/admin/grants",
            json={
                "skill_id": skill_id,
                "principal_type": "user",
                "principal_id": alice.id,
            },
        )
        assert bad2.status_code == 403


def test_audit_lists_sync_and_grant(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills_path = _write_skills_tree(tmp_path / "skills")
    monkeypatch.setenv("FSA_SKILLS_ROOT", str(skills_path))
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-123")
    from app.main import app

    with TestClient(app) as c:
        c.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-pass-123"},
        )
        c.post("/api/v1/admin/skills/sync", json={})
        items = c.get("/api/v1/skills?scope=runnable").json()["items"]
        sid = items[0]["id"]
        c.put(
            "/api/v1/admin/grants",
            json={
                "skill_id": sid,
                "principal_type": "role",
                "principal_id": "user",
            },
        )
        audit = c.get("/api/v1/admin/audit?limit=20")
        assert audit.status_code == 200
        actions = {a["action"] for a in audit.json()["items"]}
        assert "skills.sync" in actions
        assert "skills.grant" in actions
        assert "auth.login" in actions


def test_catalog_compat_after_sync(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills_path = _write_skills_tree(tmp_path / "skills")
    monkeypatch.setenv("FSA_SKILLS_ROOT", str(skills_path))
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-123")
    from app.main import app

    with TestClient(app) as c:
        c.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-pass-123"},
        )
        c.post("/api/v1/admin/skills/sync", json={})
        cat = c.get("/api/v1/skills-catalog")
        assert cat.status_code == 200
        body = cat.json()
        assert body["source"] == "db"
        assert len(body["items"]) >= 2
