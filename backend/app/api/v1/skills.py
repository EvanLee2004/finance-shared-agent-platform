"""Skills list / sync / grants."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.v1.deps import ConnDep, get_current_user
from app.services import skill_service
from app.services.auth_service import UserRecord

router = APIRouter(tags=["skills"])

CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


class GrantBody(BaseModel):
    skill_id: str = Field(min_length=1)
    principal_type: Literal["user", "role"] = "user"
    principal_id: str = Field(min_length=1)


class SyncBody(BaseModel):
    pull: bool = False


@router.get("/skills")
def list_skills(
    conn: ConnDep,
    user: CurrentUser,
    scope: str = Query(default="runnable"),
) -> dict[str, Any]:
    items = skill_service.list_skills(
        conn, user_id=user.id, role=user.role, scope=scope
    )
    return {"items": items, "scope": scope}


@router.get("/skills/{skill_id}")
def get_skill(skill_id: str, conn: ConnDep, user: CurrentUser) -> dict[str, Any]:
    return {"skill": skill_service.get_skill(conn, user_id=user.id, role=user.role, skill_id=skill_id)}


@router.post("/admin/skills/sync")
def sync_skills(body: SyncBody, conn: ConnDep, user: CurrentUser) -> dict[str, Any]:
    return skill_service.sync_from_local(
        conn, actor_user_id=user.id, actor_role=user.role, pull=body.pull
    )


@router.put("/admin/grants")
def put_grant(body: GrantBody, conn: ConnDep, user: CurrentUser) -> dict[str, Any]:
    grant = skill_service.grant_run(
        conn,
        actor_user_id=user.id,
        actor_role=user.role,
        skill_id=body.skill_id,
        principal_type=body.principal_type,
        principal_id=body.principal_id,
    )
    return {"grant": grant}


@router.get("/admin/audit")
def admin_audit(
    conn: ConnDep,
    user: CurrentUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    return {"items": skill_service.list_audit(conn, actor_role=user.role, limit=limit)}
