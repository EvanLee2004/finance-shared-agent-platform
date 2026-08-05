"""Current user + dashboard stats."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.v1.deps import ConnDep, get_current_user
from app.services import skill_service
from app.services.auth_service import UserRecord
from app.services.chat_service import list_chats

router = APIRouter(tags=["me"])

CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


@router.get("/me")
def me(user: CurrentUser) -> dict[str, Any]:
    return {"user": user.public_dict()}


@router.get("/dashboard/stats")
def dashboard_stats(conn: ConnDep, user: CurrentUser) -> dict[str, Any]:
    """Workbench numbers: published total, my runnable, my chats (story 1)."""
    published = conn.execute(
        """
        SELECT COUNT(*) AS c FROM skills
        WHERE deleted_at IS NULL AND visibility = 'published'
        """
    ).fetchone()
    skill_total = int(published["c"] if published else 0)
    runnable = skill_service.list_skills(
        conn, user_id=user.id, role=user.role, scope="runnable"
    )
    mine_owned = skill_service.list_skills(
        conn, user_id=user.id, role=user.role, scope="mine"
    )
    chats = list_chats(conn, user.id)
    return {
        "skill_total": skill_total,
        "skill_mine": len(mine_owned),
        "skill_runnable": len(runnable),
        "chat_count": len(chats),
    }
