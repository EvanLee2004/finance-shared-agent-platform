"""Apply schema_mvp.sql and ensure schema_meta.version=1."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1
_SCHEMA_FILE = Path(__file__).resolve().parent / "schema_mvp.sql"


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def schema_sql_path() -> Path:
    return _SCHEMA_FILE


def apply_schema(conn: sqlite3.Connection) -> int:
    """Execute full schema_mvp.sql and upsert schema_meta.version.

    Returns SCHEMA_VERSION after apply.
    """
    sql = _SCHEMA_FILE.read_text(encoding="utf-8")
    conn.executescript(sql)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO schema_meta(key, value, updated_at)
        VALUES ('version', ?, ?)
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          updated_at = excluded.updated_at
        """,
        (str(SCHEMA_VERSION), now),
    )
    conn.commit()
    return SCHEMA_VERSION


def get_schema_version(conn: sqlite3.Connection) -> int | None:
    row = conn.execute(
        "SELECT value FROM schema_meta WHERE key = 'version'"
    ).fetchone()
    if row is None:
        return None
    return int(row[0] if not isinstance(row, sqlite3.Row) else row["value"])


def migrate(conn: sqlite3.Connection) -> int:
    """Idempotent migrate: apply schema and return version."""
    return apply_schema(conn)
