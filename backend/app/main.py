"""Finance shared agent platform API — Phase0 foundation."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.v1 import auth, chats, health, me, system
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
    version="0.1.0-phase0",
    lifespan=lifespan,
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(me.router, prefix="/api/v1")
app.include_router(health.router, prefix="/api/v1")
app.include_router(chats.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "finance-shared-agent-platform",
        "phase": "phase0",
        "docs": "/docs",
    }
