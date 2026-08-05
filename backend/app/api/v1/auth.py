"""Auth routes: login, logout, change-password."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, Field

from app.api.v1.deps import ConnDep, client_ip
from app.domain.errors import AppError
from app.services import auth_service
from app.services.auth_service import COOKIE_NAME, SESSION_HOURS

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginBody(BaseModel):
    username: str
    password: str


class ChangePasswordBody(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)


def _error_body(exc: AppError) -> dict[str, Any]:
    return {"code": exc.code, "message": exc.message}


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response, conn: ConnDep) -> dict[str, Any]:
    try:
        user, token = auth_service.login(
            conn,
            username=body.username,
            password=body.password,
            ip=client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except AppError as exc:
        response.status_code = exc.status_code
        return _error_body(exc)

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=SESSION_HOURS * 3600,
    )
    return {"user": user.public_dict()}


@router.post("/logout")
def logout(request: Request, response: Response, conn: ConnDep) -> dict[str, str]:
    token = request.cookies.get(COOKIE_NAME)
    auth_service.logout(conn, raw_token=token, ip=client_ip(request))
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"status": "ok"}


@router.post("/change-password")
def change_password(
    body: ChangePasswordBody,
    request: Request,
    response: Response,
    conn: ConnDep,
) -> dict[str, Any]:
    token = request.cookies.get(COOKIE_NAME)
    try:
        user, _session = auth_service.resolve_session(conn, token)
        auth_service.change_password(
            conn,
            user=user,
            old_password=body.old_password,
            new_password=body.new_password,
            ip=client_ip(request),
        )
    except AppError as exc:
        response.status_code = exc.status_code
        return _error_body(exc)

    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"status": "ok"}
