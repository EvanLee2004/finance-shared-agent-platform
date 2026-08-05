"""System helpers: OC enable guide, skills catalog (read-only stub)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.adapters.oc_client import OcClient, enable_guide
from app.api.v1.deps import ConnDep, get_current_user
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
def skills_catalog(
    conn: ConnDep,
    user: CurrentUser,
) -> dict[str, Any]:
    """Compat: prefer DB published∩grant; fall back to static notes if empty."""
    from app.services import skill_service

    items = skill_service.list_skills(
        conn, user_id=user.id, role=user.role, scope="runnable"
    )
    if items:
        return {
            "items": [
                {
                    "skill_key": s["skill_key"],
                    "title": s["title"],
                    "summary": s["summary"],
                    "visibility": s["visibility"],
                    "requires_opencode": True,
                    "runnable": s.get("runnable"),
                    "current_version": s.get("current_version"),
                }
                for s in items
            ],
            "note": "来自本地/Gitee 同步的 published∩授权技能；管理员默认可跑全部 published。",
            "source": "db",
        }
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
        "note": "尚未同步 Skills 仓；管理员可 POST /api/v1/admin/skills/sync（FSA_SKILLS_ROOT）。",
        "source": "static_fallback",
    }
