"""G4: health / ready — OC down still health 200 with schema_version."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_200_with_schema_version_when_oc_down(client: TestClient) -> None:
    r = client.get("/api/v1/health")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "schema_version" in body
    assert body["schema_version"] == 1
    assert body["status"] in ("ok", "degraded")
    assert body["db"]["ok"] is True
    assert "opencode" in body
    assert body["opencode"]["ok"] is False
    assert "endpoint" in body["opencode"]


def test_ready_true_when_db_migrated(client: TestClient) -> None:
    r = client.get("/api/v1/ready")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ready"] is True
    assert body["schema_version"] == 1
    assert body["db"]["ok"] is True


def test_health_oc_probe_only_via_adapter() -> None:
    """Structural: OcClient.probe is defined only under adapters."""
    from app.adapters.oc_client import OcClient

    result = OcClient(base_url="http://127.0.0.1:1").probe()
    assert result.ok is False
    d = result.as_dict()
    assert d["ok"] is False
