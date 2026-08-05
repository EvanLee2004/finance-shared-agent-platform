"""Current user endpoint."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.api.v1.deps import get_current_user
from app.services.auth_service import UserRecord

router = APIRouter(tags=["me"])

CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


@router.get("/me")
def me(user: CurrentUser) -> dict[str, Any]:
    return {"user": user.public_dict()}
