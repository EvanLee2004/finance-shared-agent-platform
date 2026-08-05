"""Chat API — list/create/messages; isolation by user_id."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.v1.deps import ConnDep, get_current_user
from app.services import chat_service
from app.services.auth_service import UserRecord

router = APIRouter(prefix="/chats", tags=["chats"])

CurrentUser = Annotated[UserRecord, Depends(get_current_user)]


class CreateChatBody(BaseModel):
    title: str = Field(default="新对话", max_length=200)


class SendMessageBody(BaseModel):
    content: str = Field(min_length=1, max_length=50000)
    # Optional model selection from OC list (providerID + modelID)
    provider_id: str | None = Field(default=None, alias="providerID", max_length=200)
    model_id: str | None = Field(default=None, alias="modelID", max_length=400)

    model_config = {"populate_by_name": True}


@router.get("")
def list_chats(conn: ConnDep, user: CurrentUser) -> dict[str, Any]:
    items = chat_service.list_chats(conn, user.id)
    return {"items": items}


@router.post("")
def create_chat(body: CreateChatBody, conn: ConnDep, user: CurrentUser) -> dict[str, Any]:
    chat = chat_service.create_chat(
        conn,
        user_id=user.id,
        title=body.title,
    )
    return {"chat": chat}


@router.get("/{chat_id}")
def get_chat(chat_id: str, conn: ConnDep, user: CurrentUser) -> dict[str, Any]:
    return {"chat": chat_service.get_chat(conn, user.id, chat_id)}


@router.get("/{chat_id}/messages")
def get_messages(
    chat_id: str,
    conn: ConnDep,
    user: CurrentUser,
    after_seq: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items = chat_service.list_messages(conn, user.id, chat_id, after_seq=after_seq)
    return {"items": items}


@router.post("/{chat_id}/messages")
def post_message(
    chat_id: str,
    body: SendMessageBody,
    conn: ConnDep,
    user: CurrentUser,
) -> dict[str, Any]:
    # MVP: synchronous assistant reply (or human-readable OC error)
    result = chat_service.send_message(
        conn,
        user_id=user.id,
        chat_id=chat_id,
        text=body.content,
        provider_id=body.provider_id,
        model_id=body.model_id,
    )
    return result
