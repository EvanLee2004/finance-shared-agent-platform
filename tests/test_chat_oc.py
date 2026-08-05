"""Chat isolation + OC mock / OC-down send policy."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.adapters.oc_client import OcClient, OcProbeResult, extract_assistant_text
from app.db.connection import connect
from app.db.migrate import migrate
from app.services import auth_service, chat_service


def test_extract_assistant_text_error_payload() -> None:
    text = extract_assistant_text(
        {
            "info": {
                "error": {
                    "name": "ProviderAuthError",
                    "data": {"message": "missing API key"},
                }
            },
            "parts": [],
        }
    )
    assert "OpenCode 错误" in text
    assert "missing API key" in text


def test_oc_probe_down() -> None:
    client = OcClient(base_url="http://127.0.0.1:1")
    r = client.probe()
    assert r.ok is False
    d = r.as_dict()
    assert d["ok"] is False
    assert d["required"] is False
    assert d["mode"] == "optional"


def test_health_includes_oc_fields(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert "opencode" in body
    assert body["opencode"]["ok"] is False
    assert body["schema_version"] == 1
    assert body["capabilities"]["opencode_optional"] is True


def test_chat_isolation_user_b_cannot_read_a(
    data_root, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FSA_OPENCODE_BASE_URL", "http://127.0.0.1:1")
    from app.main import app

    with TestClient(app) as c:
        # create two users via service
        conn = connect(data_root / "app.db")
        migrate(conn)
        uid_a = auth_service.create_user(
            conn, username="usera", password="pass-aaaa-1", display_name="A"
        )
        uid_b = auth_service.create_user(
            conn, username="userb", password="pass-bbbb-1", display_name="B"
        )
        conn.commit()

        with patch.object(OcClient, "probe", return_value=OcProbeResult(ok=False, endpoint="x")):
            chat = chat_service.create_chat(conn, user_id=uid_a, title="A only", bind_oc=False)
        chat_id = chat["id"]
        conn.close()

        # login as B
        login = c.post(
            "/api/v1/auth/login",
            json={"username": "userb", "password": "pass-bbbb-1"},
        )
        assert login.status_code == 200
        r = c.get(f"/api/v1/chats/{chat_id}")
        assert r.status_code == 404
        assert r.json()["code"] == "not_found"
        r2 = c.get(f"/api/v1/chats/{chat_id}/messages")
        assert r2.status_code == 404


def test_send_when_oc_down_returns_oc_unavailable(admin_client: TestClient) -> None:
    login = admin_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin-pass-123"},
    )
    assert login.status_code == 200

    with patch.object(
        OcClient, "probe", return_value=OcProbeResult(ok=False, endpoint="127.0.0.1:4096")
    ):
        created = admin_client.post("/api/v1/chats", json={"title": "offline"})
        assert created.status_code == 200
        chat_id = created.json()["chat"]["id"]

        send = admin_client.post(
            f"/api/v1/chats/{chat_id}/messages",
            json={"content": "hello"},
        )
        assert send.status_code == 503
        body = send.json()
        assert body["code"] == "oc_unavailable"
        assert "OpenCode" in body["message"]


def test_send_with_mock_oc_success(admin_client: TestClient) -> None:
    assert (
        admin_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-pass-123"},
        ).status_code
        == 200
    )

    mock = MagicMock(spec=OcClient)
    mock.probe.return_value = OcProbeResult(
        ok=True, endpoint="http://127.0.0.1:4096", version="1.18.3"
    )
    mock.create_session.return_value = {"id": "oc-sess-1"}
    mock.send_message.return_value = {
        "parts": [{"type": "text", "text": "mock reply ok"}],
    }

    with patch("app.api.v1.chats.OcClient", return_value=mock):
        with patch("app.services.chat_service.OcClient", return_value=mock):
            created = admin_client.post("/api/v1/chats", json={"title": "online"})
            assert created.status_code == 200
            chat_id = created.json()["chat"]["id"]
            send = admin_client.post(
                f"/api/v1/chats/{chat_id}/messages",
                json={"content": "ping"},
            )
            assert send.status_code == 200, send.text
            body = send.json()
            assert body["user_message"]["content_text"] == "ping"
            assert "mock reply ok" in body["assistant_message"]["content_text"]

            hist = admin_client.get(f"/api/v1/chats/{chat_id}/messages")
            assert hist.status_code == 200
            assert len(hist.json()["items"]) >= 2


def test_enable_guide_requires_auth(admin_client: TestClient) -> None:
    # no cookie
    r = admin_client.get("/api/v1/opencode/enable-guide")
    assert r.status_code == 401

    assert (
        admin_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-pass-123"},
        ).status_code
        == 200
    )
    g = admin_client.get("/api/v1/opencode/enable-guide")
    assert g.status_code == 200
    body = g.json()
    assert body["commands"]
    assert any("opencode serve" in c["cmd"] for c in body["commands"])
