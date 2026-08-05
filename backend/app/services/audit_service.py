"""Append-only audit events."""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from app.db.migrate import utc_now
from app.domain.ids import new_id


def write_audit(
    conn: sqlite3.Connection,
    *,
    action: str,
    resource_type: str,
    summary: str,
    actor_user_id: str | None = None,
    resource_id: str | None = None,
    chat_id: str | None = None,
    job_id: str | None = None,
    trace_id: str | None = None,
    ip: str | None = None,
    detail: dict[str, Any] | None = None,
) -> str:
    event_id = new_id()
    detail_json = json.dumps(detail, ensure_ascii=False) if detail is not None else None
    conn.execute(
        """
        INSERT INTO audit_events(
          id, ts, actor_user_id, action, resource_type, resource_id,
          chat_id, job_id, trace_id, ip, summary, detail_json, payload_sha256
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            event_id,
            utc_now(),
            actor_user_id,
            action,
            resource_type,
            resource_id,
            chat_id,
            job_id,
            trace_id,
            ip,
            summary,
            detail_json,
        ),
    )
    return event_id
