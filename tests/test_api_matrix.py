"""W8: drive every implemented /api/v1 route + error envelope samples."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.oc_client import OcClient, OcProbeResult
from app.db.connection import connect
from app.db.migrate import migrate
from app.services import auth_service


def _login(c: TestClient, user: str = "admin", pw: str = "admin-pass-123"):
    r = c.post("/api/v1/auth/login", json={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return r


def test_validation_error_envelope(admin_client: TestClient) -> None:
    r = admin_client.post("/api/v1/auth/login", json={})
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == "validation_error"
    assert "message" in body
    assert "无效" in body["message"] or "参数" in body["message"]


def test_unauthenticated_protected_routes_401(admin_client: TestClient) -> None:
    """Unauthenticated access must be 401 + code, never 500."""
    cases = [
        ("GET", "/api/v1/me", None),
        ("GET", "/api/v1/chats", None),
        ("POST", "/api/v1/chats", {"title": "x"}),
        ("GET", "/api/v1/skills", None),
        ("GET", "/api/v1/skills-catalog", None),
        ("GET", "/api/v1/opencode/status", None),
        ("GET", "/api/v1/opencode/models", None),
        ("GET", "/api/v1/opencode/enable-guide", None),
        ("POST", "/api/v1/admin/skills/sync", {"pull": False}),
        (
            "PUT",
            "/api/v1/admin/grants",
            {
                "skill_id": "x",
                "principal_type": "user",
                "principal_id": "y",
            },
        ),
        ("GET", "/api/v1/admin/audit", None),
        (
            "POST",
            "/api/v1/auth/change-password",
            {"old_password": "a", "new_password": "b12345678"},
        ),
    ]
    for method, path, body in cases:
        if method == "GET":
            r = admin_client.get(path)
        elif method == "POST":
            r = admin_client.post(path, json=body or {})
        else:
            r = admin_client.put(path, json=body or {})
        assert r.status_code == 401, f"{method} {path} -> {r.status_code} {r.text}"
        data = r.json()
        assert data.get("code") == "auth_required", f"{path}: {data}"
        assert data.get("message")


def test_health_oc_down_still_ok_and_login_workbench(
    data_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FSA_OPENCODE_BASE_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-123")
    from app.main import app

    with TestClient(app) as c:
        h = c.get("/api/v1/health")
        assert h.status_code == 200
        body = h.json()
        assert body["db"]["ok"] is True
        assert body["opencode"]["ok"] is False
        assert body["opencode"].get("required") is False
        assert body["capabilities"]["opencode_optional"] is True
        assert body["capabilities"]["login_workbench"] is True

        _login(c)
        me = c.get("/api/v1/me")
        assert me.status_code == 200
        # skills catalog usable without OC
        cat = c.get("/api/v1/skills-catalog")
        assert cat.status_code == 200
        skills = c.get("/api/v1/skills?scope=runnable")
        assert skills.status_code == 200


def test_matrix_smoke_all_implemented_endpoints(
    data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise every shipped /api/v1 route on real app entry (happy + key fails)."""
    skills_root = tmp_path / "skills"
    skills_root.mkdir()
    (skills_root / "catalog.yaml").write_text(
        """
skills:
  - id: w8-alpha
    version: "0.1.0"
    summary: "W8 matrix skill"
    path: skills/w8-alpha
""",
        encoding="utf-8",
    )
    (skills_root / "skills" / "w8-alpha").mkdir(parents=True)
    (skills_root / "skills" / "w8-alpha" / "SKILL.md").write_text("# a\n", encoding="utf-8")
    monkeypatch.setenv("FSA_SKILLS_ROOT", str(skills_root))
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_USER", "admin")
    monkeypatch.setenv("FSA_BOOTSTRAP_ADMIN_PASSWORD", "admin-pass-123")
    monkeypatch.setenv("FSA_OPENCODE_BASE_URL", "http://127.0.0.1:1")
    from app.main import app

    results: list[str] = []

    def rec(name: str, ok: bool, detail: str = "") -> None:
        results.append(f"{'PASS' if ok else 'FAIL'} {name} {detail}".strip())

    with TestClient(app) as c:
        # public
        r = c.get("/api/v1/health")
        rec("GET /health", r.status_code == 200 and r.json()["opencode"]["ok"] is False)
        r = c.get("/api/v1/ready")
        rec("GET /ready", r.status_code == 200 and r.json().get("ready") is True)

        # auth
        r = c.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
        rec(
            "POST /auth/login fail",
            r.status_code == 401 and r.json()["code"] == "auth_failed",
        )
        r = _login(c)
        rec("POST /auth/login ok", r.status_code == 200 and "user" in r.json())

        r = c.get("/api/v1/me")
        rec("GET /me", r.status_code == 200 and r.json()["user"]["role"] == "admin")

        # system / oc
        r = c.get("/api/v1/opencode/status")
        rec("GET /opencode/status", r.status_code == 200 and "opencode" in r.json())
        r = c.get("/api/v1/opencode/enable-guide")
        rec(
            "GET /opencode/enable-guide",
            r.status_code == 200 and "commands" in r.json(),
        )
        r = c.get("/api/v1/opencode/models")
        rec(
            "GET /opencode/models",
            r.status_code == 200 and r.json().get("ok") is False,
        )

        # skills
        r = c.post("/api/v1/admin/skills/sync", json={"pull": False})
        rec("POST /admin/skills/sync", r.status_code == 200 and r.json().get("ok") is True)
        r = c.get("/api/v1/skills?scope=runnable")
        rec("GET /skills", r.status_code == 200 and len(r.json().get("items", [])) >= 1)
        skill_id = r.json()["items"][0]["id"]
        r = c.get(f"/api/v1/skills/{skill_id}")
        rec("GET /skills/{id}", r.status_code == 200 and "skill" in r.json())
        r = c.get("/api/v1/skills-catalog")
        rec("GET /skills-catalog", r.status_code == 200 and "items" in r.json())

        # grants + audit
        conn = connect(data_root / "app.db")
        migrate(conn)
        uid = auth_service.create_user(
            conn, username="bob", password="bob-pass-99", display_name="Bob"
        )
        conn.commit()
        conn.close()
        r = c.put(
            "/api/v1/admin/grants",
            json={
                "skill_id": skill_id,
                "principal_type": "user",
                "principal_id": uid,
            },
        )
        rec("PUT /admin/grants", r.status_code == 200 and "grant" in r.json())
        r = c.get("/api/v1/admin/audit?limit=10")
        rec("GET /admin/audit", r.status_code == 200 and "items" in r.json())

        # chats + OC down send
        r = c.post("/api/v1/chats", json={"title": "w8"})
        rec("POST /chats", r.status_code == 200 and "chat" in r.json())
        chat_id = r.json()["chat"]["id"]
        r = c.get("/api/v1/chats")
        rec("GET /chats", r.status_code == 200 and "items" in r.json())
        r = c.get(f"/api/v1/chats/{chat_id}")
        rec("GET /chats/{id}", r.status_code == 200)
        r = c.get(f"/api/v1/chats/{chat_id}/messages")
        rec("GET /chats/{id}/messages", r.status_code == 200)
        r = c.post(
            f"/api/v1/chats/{chat_id}/messages",
            json={"content": "ping"},
        )
        rec(
            "POST messages OC down",
            r.status_code == 503 and r.json().get("code") == "oc_unavailable",
            r.text[:120],
        )

        # isolation
        c.cookies.clear()
        r = c.post(
            "/api/v1/auth/login",
            json={"username": "bob", "password": "bob-pass-99"},
        )
        assert r.status_code == 200
        r = c.get(f"/api/v1/chats/{chat_id}")
        rec(
            "isolation GET chat as bob",
            r.status_code == 404 and r.json().get("code") == "not_found",
        )
        r = c.post("/api/v1/admin/skills/sync", json={})
        rec(
            "forbidden sync as bob",
            r.status_code == 403 and r.json().get("code") == "forbidden",
        )

        # change-password + logout as admin again
        c.cookies.clear()
        _login(c)
        r = c.post(
            "/api/v1/auth/change-password",
            json={"old_password": "admin-pass-123", "new_password": "admin-pass-999"},
        )
        rec("POST /auth/change-password", r.status_code == 200)
        _login(c, pw="admin-pass-999")
        r = c.post("/api/v1/auth/logout")
        rec("POST /auth/logout", r.status_code == 200)
        r = c.get("/api/v1/me")
        rec("GET /me after logout", r.status_code == 401)

    fails = [x for x in results if x.startswith("FAIL")]
    report = "\n".join(results)
    assert not fails, "Matrix failures:\n" + report


def test_oc_http_only_via_adapter_module() -> None:
    """Structural: OC HTTP lives only in adapters/oc_client.py."""
    root = Path(__file__).resolve().parents[1] / "backend" / "app"
    hits = []
    for path in root.rglob("*.py"):
        if path.name == "oc_client.py":
            continue
        text = path.read_text(encoding="utf-8")
        # second HTTP client talking to OC session/model APIs
        if "httpx" in text and (
            "/session" in text or "/api/model" in text or "/global/health" in text
        ):
            hits.append(str(path.relative_to(root)))
        if "DEFAULT_OC_BASE" in text:
            hits.append(f"{path.name}:DEFAULT_OC_BASE")
    assert hits == [], hits
