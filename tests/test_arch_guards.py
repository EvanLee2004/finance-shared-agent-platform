"""W9 architecture guards — OC single egress, layer import direction, domain enums."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "backend" / "app"


def _py_files(rel: str) -> list[Path]:
    return sorted((APP / rel).rglob("*.py"))


def test_api_layer_does_not_import_oc_client() -> None:
    """Routes must use services; only adapters/oc_client + oc_service may touch OC HTTP."""
    hits = []
    for path in _py_files("api"):
        text = path.read_text(encoding="utf-8")
        if "adapters.oc_client" in text or "from app.adapters import oc_client" in text:
            hits.append(str(path.relative_to(APP)))
    assert hits == [], f"api layer imports oc_client: {hits}"


def test_only_oc_client_and_oc_service_use_httpx_for_oc_paths() -> None:
    """httpx + OC session/model paths must stay in oc_client (service may wrap)."""
    allowed = {"adapters/oc_client.py"}
    hits = []
    for path in APP.rglob("*.py"):
        rel = path.relative_to(APP).as_posix()
        if rel in allowed:
            continue
        text = path.read_text(encoding="utf-8")
        if "httpx" not in text:
            continue
        if any(
            p in text
            for p in ("/session", "/api/model", "/global/health", "opencode.ai/install")
        ):
            # allow enable_guide strings only in oc_client
            hits.append(rel)
    assert hits == [], f"scattered OC HTTP: {hits}"


def test_domain_enums_define_audit_and_roles() -> None:
    from app.domain import enums

    assert enums.ROLE_ADMIN == "admin"
    assert enums.AUDIT_SKILLS_SYNC == "skills.sync"
    assert enums.AUDIT_CHAT_CREATE == "chat.create"
    assert enums.VIS_PUBLISHED == "published"


def test_frontend_does_not_construct_oc_urls() -> None:
    fe = ROOT / "frontend" / "src"
    hits = []
    for path in fe.rglob("*"):
        if path.suffix not in {".vue", ".js", ".ts"}:
            continue
        text = path.read_text(encoding="utf-8")
        if "127.0.0.1:4096" in text or "opencode serve" in text and "fetch(" in text:
            hits.append(str(path.relative_to(ROOT)))
        if "FSA_OPENCODE" in text:
            hits.append(str(path.relative_to(ROOT)))
    assert hits == [], hits


def test_no_services_import_from_api() -> None:
    """Dependency rule: services must not import api routes."""
    hits = []
    for path in _py_files("services"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("app.api"):
                    hits.append(f"{path.name}:{node.module}")
    assert hits == [], hits
