"""Finance shared agent platform API — Phase0 foundation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1 import auth, chats, health, me, skills, system
from app.db.connection import connect, db_path
from app.db.migrate import migrate
from app.domain.errors import AppError
from app.services.auth_service import bootstrap_admin_if_needed


@asynccontextmanager
async def lifespan(_app: FastAPI):
    conn = connect(db_path())
    try:
        migrate(conn)
        bootstrap_admin_if_needed(conn)
        conn.commit()
    finally:
        conn.close()
    yield


app = FastAPI(
    title="财务共享中台 Agent",
    version="0.2.0-night",
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(chats.router, prefix="/api/v1")
app.include_router(skills.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Stable envelope: code + Chinese message (design 05 error table)."""
    errors = exc.errors()
    parts: list[str] = []
    for err in errors[:5]:
        loc = ".".join(str(x) for x in err.get("loc", ()) if x != "body")
        msg = err.get("msg") or "无效"
        if loc:
            parts.append(f"{loc}: {msg}")
        else:
            parts.append(str(msg))
    message = "请求参数无效"
    if parts:
        message = "请求参数无效：" + "；".join(parts)
    return JSONResponse(
        status_code=422,
        content={
            "code": "validation_error",
            "message": message,
            "detail": errors,
        },
    )


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "finance-shared-agent-platform",
        "phase": "night",
        "docs": "/docs",
    }
