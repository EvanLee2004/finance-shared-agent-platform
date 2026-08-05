"""Chat sessions + messages; 1 mid-platform chat ↔ 1 OC session."""

from __future__ import annotations

import sqlite3
from typing import Any

from app.adapters.oc_client import (
    OcClient,
    extract_assistant_text,
    extract_session_id,
)
from app.db.migrate import utc_now
from app.domain.errors import NotFound, OcUnavailable, ValidationError
from app.domain.ids import new_id
from app.services.audit_service import write_audit


def _chat_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "title": row["title"],
        "status": row["status"],
        "opencode_session_id": row["opencode_session_id"],
        "work_dir_rel": row["work_dir_rel"],
        "last_message_at": row["last_message_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "oc_bound": bool(row["opencode_session_id"]),
    }


def _msg_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "chat_id": row["chat_id"],
        "user_id": row["user_id"],
        "role": row["role"],
        "seq": row["seq"],
        "content_text": row["content_text"],
        "created_at": row["created_at"],
    }


def list_chats(conn: sqlite3.Connection, user_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM chat_sessions
        WHERE user_id = ? AND deleted_at IS NULL
        ORDER BY COALESCE(last_message_at, created_at) DESC
        """,
        (user_id,),
    ).fetchall()
    return [_chat_row(r) for r in rows]


def get_chat(conn: sqlite3.Connection, user_id: str, chat_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT * FROM chat_sessions
        WHERE id = ? AND deleted_at IS NULL
        """,
        (chat_id,),
    ).fetchone()
    if row is None or row["user_id"] != user_id:
        # isolation: do not reveal existence
        raise NotFound("会话不存在")
    return _chat_row(row)


def create_chat(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    title: str = "新对话",
    oc: OcClient | None = None,
    bind_oc: bool = True,
) -> dict[str, Any]:
    """Create chat row. Optionally bind OC session if OC is up."""
    chat_id = new_id()
    now = utc_now()
    work_dir = f"workspaces/{user_id}/{chat_id}"
    oc_session_id: str | None = None
    status = "active"

    client = oc or OcClient()
    if bind_oc:
        probe = client.probe()
        if probe.ok:
            try:
                created = client.create_session(title=title or "新对话")
                oc_session_id = extract_session_id(created)
            except Exception:
                # Chat still usable offline; send will require OC
                oc_session_id = None

    conn.execute(
        """
        INSERT INTO chat_sessions(
          id, user_id, title, status, opencode_session_id, work_dir_rel,
          model_hint, last_message_at, created_at, updated_at, deleted_at
        ) VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, NULL)
        """,
        (chat_id, user_id, title or "新对话", status, oc_session_id, work_dir, now, now),
    )
    write_audit(
        conn,
        action="chat.create",
        resource_type="chat",
        resource_id=chat_id,
        actor_user_id=user_id,
        chat_id=chat_id,
        summary=f"create chat oc_bound={bool(oc_session_id)}",
    )
    conn.commit()
    return get_chat(conn, user_id, chat_id)


def list_messages(
    conn: sqlite3.Connection, user_id: str, chat_id: str, after_seq: int = 0
) -> list[dict[str, Any]]:
    get_chat(conn, user_id, chat_id)
    rows = conn.execute(
        """
        SELECT * FROM chat_messages
        WHERE chat_id = ? AND seq > ?
        ORDER BY seq ASC
        """,
        (chat_id, after_seq),
    ).fetchall()
    return [_msg_row(r) for r in rows]


def _next_seq(conn: sqlite3.Connection, chat_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) AS m FROM chat_messages WHERE chat_id = ?",
        (chat_id,),
    ).fetchone()
    return int(row["m"]) + 1


def _ensure_oc_session(
    conn: sqlite3.Connection,
    chat: dict[str, Any],
    client: OcClient,
) -> str:
    if chat.get("opencode_session_id"):
        return str(chat["opencode_session_id"])
    probe = client.probe()
    if not probe.ok:
        raise OcUnavailable()
    try:
        created = client.create_session(title=chat.get("title") or "新对话")
        oc_id = extract_session_id(created)
    except Exception as exc:
        raise OcUnavailable(f"无法创建 OpenCode 会话：{type(exc).__name__}") from exc
    if not oc_id:
        raise OcUnavailable("OpenCode 返回了无效的 session id")
    now = utc_now()
    conn.execute(
        """
        UPDATE chat_sessions
        SET opencode_session_id = ?, updated_at = ?
        WHERE id = ?
        """,
        (oc_id, now, chat["id"]),
    )
    conn.commit()
    return oc_id


def send_message(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    chat_id: str,
    text: str,
    oc: OcClient | None = None,
) -> dict[str, Any]:
    """Persist user msg; require OC for assistant; return both messages."""
    text = (text or "").strip()
    if not text:
        raise ValidationError("消息不能为空")

    chat = get_chat(conn, user_id, chat_id)
    client = oc or OcClient()
    now = utc_now()

    # Always allow browsing history; send needs OC
    probe = client.probe()
    if not probe.ok and not chat.get("opencode_session_id"):
        raise OcUnavailable()

    user_seq = _next_seq(conn, chat_id)
    user_msg_id = new_id()
    conn.execute(
        """
        INSERT INTO chat_messages(
          id, chat_id, user_id, role, seq, content_text, content_path,
          content_sha256, token_count_est, opencode_message_ref, client_message_id,
          created_at
        ) VALUES (?, ?, ?, 'user', ?, ?, NULL, NULL, NULL, NULL, NULL, ?)
        """,
        (user_msg_id, chat_id, user_id, user_seq, text, now),
    )
    conn.execute(
        """
        UPDATE chat_sessions
        SET last_message_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (now, now, chat_id),
    )
    conn.commit()

    try:
        oc_session_id = _ensure_oc_session(conn, chat, client)
        oc_resp = client.send_message(oc_session_id, text)
        assistant_text = extract_assistant_text(oc_resp)
    except OcUnavailable:
        raise
    except Exception as exc:
        assistant_text = f"[OpenCode 调用失败] {type(exc).__name__}: {exc}"

    asst_seq = _next_seq(conn, chat_id)
    asst_id = new_id()
    asst_now = utc_now()
    conn.execute(
        """
        INSERT INTO chat_messages(
          id, chat_id, user_id, role, seq, content_text, content_path,
          content_sha256, token_count_est, opencode_message_ref, client_message_id,
          created_at
        ) VALUES (?, ?, ?, 'assistant', ?, ?, NULL, NULL, NULL, NULL, NULL, ?)
        """,
        (asst_id, chat_id, user_id, asst_seq, assistant_text, asst_now),
    )
    conn.execute(
        """
        UPDATE chat_sessions
        SET last_message_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (asst_now, asst_now, chat_id),
    )
    write_audit(
        conn,
        action="chat.message",
        resource_type="chat",
        resource_id=chat_id,
        actor_user_id=user_id,
        chat_id=chat_id,
        summary="send message",
    )
    conn.commit()

    return {
        "user_message": {
            "id": user_msg_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "role": "user",
            "seq": user_seq,
            "content_text": text,
            "created_at": now,
        },
        "assistant_message": {
            "id": asst_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "role": "assistant",
            "seq": asst_seq,
            "content_text": assistant_text,
            "created_at": asst_now,
        },
    }
