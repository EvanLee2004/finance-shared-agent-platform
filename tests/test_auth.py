"""G2/G3: Auth HTTP surface — login, me, logout, change-password."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _login(client: TestClient, username: str = "admin", password: str = "admin-pass-123"):
    return client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )


def test_login_then_me_200(admin_client: TestClient) -> None:
    r = _login(admin_client)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["user"]["username"] == "admin"
    assert body["user"]["role"] == "admin"
    # Real Set-Cookie path: cookie jar + response header
    assert "fsa_sid" in r.cookies
    assert r.cookies.get("fsa_sid")
    set_cookie = r.headers.get("set-cookie", "")
    assert "fsa_sid=" in set_cookie
    assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()

    me = admin_client.get("/api/v1/me")
    assert me.status_code == 200, me.text
    assert me.json()["user"]["username"] == "admin"
    assert me.json()["user"]["role"] == "admin"


def test_me_without_cookie_401(admin_client: TestClient) -> None:
    # Fresh client path: no cookies after bootstrap-only request
    r = admin_client.get("/api/v1/me")
    assert r.status_code == 401
    assert r.json()["code"] == "auth_required"


def test_logout_then_me_401(admin_client: TestClient) -> None:
    assert _login(admin_client).status_code == 200
    assert admin_client.get("/api/v1/me").status_code == 200

    out = admin_client.post("/api/v1/auth/logout")
    assert out.status_code == 200

    me = admin_client.get("/api/v1/me")
    assert me.status_code == 401
    assert me.json()["code"] == "auth_required"


def test_change_password_revokes_old_cookie(admin_client: TestClient) -> None:
    login = _login(admin_client)
    assert login.status_code == 200
    old_cookie = login.cookies.get("fsa_sid")
    assert old_cookie

    assert admin_client.get("/api/v1/me").status_code == 200

    ch = admin_client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "admin-pass-123", "new_password": "new-pass-4567"},
    )
    assert ch.status_code == 200, ch.text

    # Session revoked; cookie cleared by handler
    me_after = admin_client.get("/api/v1/me")
    assert me_after.status_code == 401

    # Old raw token must not authenticate even if re-injected
    admin_client.cookies.clear()
    admin_client.cookies.set("fsa_sid", old_cookie)
    me_old = admin_client.get("/api/v1/me")
    assert me_old.status_code == 401
    assert me_old.json()["code"] == "auth_required"

    # New password works with a clean cookie jar
    admin_client.cookies.clear()
    login2 = _login(admin_client, password="new-pass-4567")
    assert login2.status_code == 200
    assert login2.cookies.get("fsa_sid")
    assert admin_client.get("/api/v1/me").status_code == 200


def test_login_failed_uniform_401(admin_client: TestClient) -> None:
    """Wrong password and unknown user both 401 auth_failed — no existence leak."""
    r = _login(admin_client, password="wrong-password")
    assert r.status_code == 401
    body_wrong = r.json()
    assert body_wrong["code"] == "auth_failed"
    assert "message" in body_wrong

    r2 = admin_client.post(
        "/api/v1/auth/login",
        json={"username": "no-such-user", "password": "x"},
    )
    assert r2.status_code == 401
    body_unknown = r2.json()
    assert body_unknown["code"] == "auth_failed"
    # Same code + same message shape: do not reveal whether username exists
    assert body_unknown["code"] == body_wrong["code"]
    assert body_unknown["message"] == body_wrong["message"]
    joined = (body_wrong["message"] + body_unknown["message"]).lower()
    assert "not found" not in joined
    assert "不存在" not in joined
    assert "unknown" not in joined


def test_login_writes_audit(admin_client: TestClient, data_root) -> None:
    from app.db.connection import connect

    assert _login(admin_client).status_code == 200
    conn = connect(data_root / "app.db")
    try:
        rows = conn.execute(
            "SELECT action FROM audit_events WHERE action = 'auth.login'"
        ).fetchall()
        assert len(rows) >= 1
    finally:
        conn.close()
