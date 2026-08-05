"""Health and readiness endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Response

from app.adapters.oc_client import OcClient
from app.api.v1.deps import ConnDep
from app.db.migrate import get_schema_version
from app.services.skill_service import repo_status

router = APIRouter(tags=["system"])


@router.get("/health")
def health(conn: ConnDep) -> dict[str, Any]:
    """Liveness-ish health: always 200 if process is up; OC failure is degraded."""
    db_ok = True
    schema_version: int | None = None
    try:
        schema_version = get_schema_version(conn)
        conn.execute("SELECT 1").fetchone()
    except Exception:  # noqa: BLE001
        db_ok = False

    oc = OcClient().probe()
    skills = repo_status()

    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "name": "finance-shared-agent-platform",
        "schema_version": schema_version if schema_version is not None else 0,
        "opencode": oc.as_dict(),
        "db": {"ok": db_ok},
        "skills_repo": skills,
        "capabilities": {
            "login_workbench": True,
            "chat_requires_opencode": True,
            "opencode_optional": True,
            "skills_sync": True,
            "grants": True,
        },
    }


@router.get("/ready")
def ready(conn: ConnDep, response: Response) -> dict[str, Any]:
    """Strict readiness: DB readable + schema migrated to version 1."""
    try:
        version = get_schema_version(conn)
        conn.execute("SELECT 1").fetchone()
        if version != 1:
            response.status_code = 503
            return {
                "ready": False,
                "db": {"ok": False, "reason": f"schema_version={version}"},
            }
        return {
            "ready": True,
            "db": {"ok": True},
            "schema_version": version,
        }
    except Exception as exc:  # noqa: BLE001
        response.status_code = 503
        return {
            "ready": False,
            "db": {"ok": False, "reason": type(exc).__name__},
        }
