"""System helpers: OC enable guide, skills catalog (read-only stub)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.adapters.oc_client import OcClient, enable_guide
from app.api.v1.deps import get_current_user
from app.services.auth_service import UserRecord

router = APIRouter(tags=["system"])

CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


@router.get("/opencode/status")
def opencode_status(_user: CurrentUser) -> dict[str, Any]:
    """Re-probe OC for workbench 「我已启动」."""
    result = OcClient().probe()
    return {"opencode": result.as_dict()}


@router.get("/opencode/enable-guide")
def opencode_enable_guide(_user: CurrentUser) -> dict[str, Any]:
    """User-confirmed setup commands — no server-side install."""
    return enable_guide()


@router.get("/opencode/models")
def opencode_models(_user: CurrentUser) -> dict[str, Any]:
    """List models from live OpenCode only — never a mid-platform whitelist."""
    return OcClient().list_models()


@router.get("/skills-catalog")
def skills_catalog(_user: CurrentUser) -> dict[str, Any]:
    """Read-only local notes (Phase0: no published skills DB required)."""
    return {
        "items": [
            {
                "skill_key": "local-notes",
                "title": "本机说明（不依赖 OpenCode）",
                "summary": "登录、工作台、主题、health 状态、OpenCode 引导均可在中台独立使用。",
                "visibility": "local",
                "requires_opencode": False,
            },
            {
                "skill_key": "chat-via-oc",
                "title": "智能对话（可选 · 依赖 OpenCode）",
                "summary": "消息经中台鉴权后转发本机 opencode serve；浏览器不直连 OC。",
                "visibility": "local",
                "requires_opencode": True,
            },
        ],
        "note": "一期业务 skill 上架与授权见后续 Phase；当前为只读本地说明。",
    }
