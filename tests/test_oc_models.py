"""Models from OpenCode only — no mid-platform hard-coded catalog."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.adapters.oc_client import OcClient, OcProbeResult


MOCK_MODELS_PAYLOAD = {
    "location": {"directory": "/tmp"},
    "data": [
        {
            "id": "deepseek-v4-flash-free",
            "providerID": "opencode",
            "name": "DeepSeek V4 Flash Free",
            "cost": [{"input": 0, "output": 0}],
            "status": "active",
            "enabled": True,
        },
        {
            "id": "some-paid-model",
            "providerID": "openrouter",
            "name": "Paid Example",
            "cost": [{"input": 1.0, "output": 2.0}],
            "status": "active",
            "enabled": True,
        },
        {
            "id": "third-model",
            "providerID": "opencode",
            "name": "Third",
            "cost": [{"input": 0, "output": 0}],
            "status": "active",
            "enabled": True,
        },
    ],
}


def test_list_models_from_mock_oc(admin_client: TestClient) -> None:
    assert (
        admin_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-pass-123"},
        ).status_code
        == 200
    )

    mock = MagicMock(spec=OcClient)
    mock.list_models.return_value = {
        "ok": True,
        "source": "/api/model",
        "items": [
            {
                "providerID": "opencode",
                "modelID": "deepseek-v4-flash-free",
                "name": "DeepSeek V4 Flash Free",
                "free": True,
                "key": "opencode/deepseek-v4-flash-free",
            },
            {
                "providerID": "openrouter",
                "modelID": "some-paid-model",
                "name": "Paid Example",
                "free": False,
                "key": "openrouter/some-paid-model",
            },
            {
                "providerID": "opencode",
                "modelID": "third-model",
                "name": "Third",
                "free": True,
                "key": "opencode/third-model",
            },
        ],
        "error": None,
    }

    with patch("app.api.v1.system.OcClient", return_value=mock):
        r = admin_client.get("/api/v1/opencode/models")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert len(body["items"]) >= 2
    ids = {(i["providerID"], i["modelID"]) for i in body["items"]}
    assert ("opencode", "deepseek-v4-flash-free") in ids
    assert ("openrouter", "some-paid-model") in ids
    # must be from mock, not invented by mid-platform
    assert body["source"] == "/api/model" or body.get("items")


def test_list_models_oc_client_parses_api_model() -> None:
    """Drive real OcClient.list_models path with httpx mocked."""
    client = OcClient(base_url="http://127.0.0.1:4096")

    class FakeResp:
        status_code = 200

        def json(self):
            return MOCK_MODELS_PAYLOAD

    class FakeHttp:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def get(self, url):
            assert url.endswith("/api/model")
            return FakeResp()

    with patch.object(
        client,
        "probe",
        return_value=OcProbeResult(ok=True, endpoint="http://127.0.0.1:4096"),
    ):
        with patch("app.adapters.oc_client.httpx.Client", FakeHttp):
            out = client.list_models()
    assert out["ok"] is True
    assert out["source"] == "/api/model"
    assert len(out["items"]) == 3
    assert out["items"][0]["modelID"] == "deepseek-v4-flash-free"
    assert out["items"][0]["providerID"] == "opencode"


def test_list_models_when_oc_down(admin_client: TestClient) -> None:
    assert (
        admin_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-pass-123"},
        ).status_code
        == 200
    )
    mock = MagicMock(spec=OcClient)
    mock.list_models.return_value = {
        "ok": False,
        "source": None,
        "items": [],
        "error": "ConnectError",
        "opencode": {"ok": False, "endpoint": "127.0.0.1:4096"},
    }
    with patch("app.api.v1.system.OcClient", return_value=mock):
        r = admin_client.get("/api/v1/opencode/models")
    assert r.status_code == 200  # never 500
    body = r.json()
    assert body["ok"] is False
    assert body["items"] == []
    assert body.get("error")


def test_send_message_forwards_selected_model(admin_client: TestClient) -> None:
    assert (
        admin_client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin-pass-123"},
        ).status_code
        == 200
    )

    captured: dict = {}

    mock = MagicMock(spec=OcClient)
    mock.probe.return_value = OcProbeResult(
        ok=True, endpoint="http://127.0.0.1:4096", version="1.18.3"
    )
    mock.create_session.return_value = {"id": "oc-sess-model"}

    def _send(session_id, text, *, provider_id=None, model_id=None):
        captured["session_id"] = session_id
        captured["text"] = text
        captured["provider_id"] = provider_id
        captured["model_id"] = model_id
        return {
            "parts": [{"type": "text", "text": f"reply-via-{provider_id}/{model_id}"}],
            "_request_model": {"providerID": provider_id, "modelID": model_id},
        }

    mock.send_message.side_effect = _send

    with patch("app.api.v1.chats.OcClient", return_value=mock):
        with patch("app.services.chat_service.OcClient", return_value=mock):
            created = admin_client.post("/api/v1/chats", json={"title": "m"})
            assert created.status_code == 200
            chat_id = created.json()["chat"]["id"]
            send = admin_client.post(
                f"/api/v1/chats/{chat_id}/messages",
                json={
                    "content": "hello model",
                    "providerID": "opencode",
                    "modelID": "deepseek-v4-flash-free",
                },
            )
            assert send.status_code == 200, send.text
            body = send.json()
            assert body["model"]["providerID"] == "opencode"
            assert body["model"]["modelID"] == "deepseek-v4-flash-free"
            assert "deepseek-v4-flash-free" in body["assistant_message"]["content_text"]

    assert captured["provider_id"] == "opencode"
    assert captured["model_id"] == "deepseek-v4-flash-free"
    assert captured["text"] == "hello model"
